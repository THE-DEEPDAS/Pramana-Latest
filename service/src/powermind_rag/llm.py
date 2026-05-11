from __future__ import annotations

import json
import re
import base64
from io import BytesIO
from pathlib import Path
from typing import Protocol
from urllib import parse, request
from urllib.error import HTTPError, URLError

from PIL import Image

from powermind_rag.rate_limit import NVIDIA_RATE_LIMITER


class ChatLLM(Protocol):
    def generate(self, system: str, user: str, max_new_tokens: int = 512) -> str:
        ...

    def generate_with_images(
        self,
        system: str,
        user: str,
        image_paths: list[Path],
        max_new_tokens: int = 512,
    ) -> str:
        ...

class LocalQwen:
    def __init__(self, model_path: Path, device: str):
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.model_path = model_path
        self.device = device
        self._validate_model_files()
        self.tokenizer = AutoTokenizer.from_pretrained(str(model_path), trust_remote_code=True)
        model_kwargs = {
            "torch_dtype": "auto",
            "trust_remote_code": True,
        }
        if device == "cuda":
            model_kwargs["device_map"] = "auto"
        self.model = AutoModelForCausalLM.from_pretrained(str(model_path), **model_kwargs)
        if device == "cpu":
            self.model.to("cpu")

    def generate(self, system: str, user: str, max_new_tokens: int = 512) -> str:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        target_device = next(self.model.parameters()).device
        inputs = self.tokenizer([prompt], return_tensors="pt").to(target_device)
        generated = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=None,
            top_p=None,
        )
        generated = generated[:, inputs.input_ids.shape[1] :]
        return self.tokenizer.batch_decode(generated, skip_special_tokens=True)[0].strip()

    def _validate_model_files(self) -> None:
        if not self.model_path.exists():
            raise RuntimeError(f"Qwen model path does not exist: {self.model_path}")
        weight_files = list(self.model_path.glob("*.safetensors")) + list(self.model_path.glob("*.bin"))
        if not weight_files:
            partial = list(self.model_path.glob("*.crdownload"))
            hint = " Partial browser downloads are present." if partial else ""
            raise RuntimeError(f"No completed Qwen weight files found in {self.model_path}.{hint}")


class LocalQwenVL:
    def __init__(self, model_path: Path, device: str):
        self.model_path = model_path
        self.device = device
        self._validate_model_files()
        try:
            from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
        except ImportError as exc:
            raise RuntimeError(
                "Install a recent transformers build that includes Qwen2.5-VL support."
            ) from exc
        self.processor = AutoProcessor.from_pretrained(str(model_path))
        model_kwargs = {
            "torch_dtype": "auto",
            "device_map": "auto" if device == "cuda" else None,
        }
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            str(model_path),
            **{k: v for k, v in model_kwargs.items() if v is not None},
        )
        if device == "cpu":
            self.model.to("cpu")

    def generate(self, system: str, user: str, max_new_tokens: int = 512) -> str:
        return self.generate_with_images(system, user, [], max_new_tokens)

    def generate_with_images(
        self,
        system: str,
        user: str,
        image_paths: list[Path],
        max_new_tokens: int = 512,
    ) -> str:
        try:
            from qwen_vl_utils import process_vision_info
        except ImportError as exc:
            raise RuntimeError("Install qwen-vl-utils to use local Qwen-VL.") from exc

        content = []
        for image_path in image_paths:
            content.append({
                "type": "image",
                "image": str(image_path),
                "max_pixels": 896 * 896,
            })
        content.append({"type": "text", "text": user})
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": content},
        ]
        prompt = self.processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[prompt],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        target_device = "cuda" if self.device == "cuda" else "cpu"
        inputs = inputs.to(target_device)
        generated_ids = self.model.generate(**inputs, max_new_tokens=max_new_tokens)
        trimmed = [
            out_ids[len(in_ids) :]
            for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = self.processor.batch_decode(
            trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )
        return output_text[0].strip()

    def unload_model(self) -> None:
        import torch

        model = getattr(self, "model", None)
        if model is not None:
            del self.model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _validate_model_files(self) -> None:
        if not self.model_path.exists():
            raise RuntimeError(f"Qwen-VL model path does not exist: {self.model_path}")
        weight_files = list(self.model_path.glob("*.safetensors")) + list(self.model_path.glob("*.bin"))
        if not weight_files:
            partial = list(self.model_path.glob("*.crdownload"))
            hint = " Partial browser downloads are present." if partial else ""
            raise RuntimeError(
                f"No completed Qwen-VL weight files found in {self.model_path}.{hint}"
            )


class GroqChatLLM:
    def __init__(self, api_key: str | None, model_name: str):
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is required when POWERMIND_GENERATION_PROVIDER=groq.")
        try:
            from groq import Groq
        except ImportError as exc:
            raise RuntimeError("Install groq to use Groq generation.") from exc
        self.client = Groq(api_key=api_key)
        self.model_name = model_name

    def generate(self, system: str, user: str, max_new_tokens: int = 512) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            temperature=0,
            max_tokens=max_new_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (response.choices[0].message.content or "").strip()


class OpenRouterChatLLM:
    def __init__(
        self,
        api_key: str | None,
        model_name: str,
        base_url: str = "https://openrouter.ai/api/v1",
        http_referer: str = "http://localhost/powermind",
        app_title: str = "PowerMind RAG",
    ):
        if not api_key:
            raise RuntimeError("OPEN_ROUTER_API_KEY is required when POWERMIND_GENERATION_PROVIDER=openrouter.")
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.http_referer = http_referer
        self.app_title = app_title

    def generate(self, system: str, user: str, max_new_tokens: int = 512) -> str:
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "max_tokens": max_new_tokens,
        }
        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": self.http_referer,
                "X-Title": self.app_title,
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"OpenRouter {self.model_name} request failed with HTTP {exc.code}: {body}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(f"OpenRouter {self.model_name} request failed: {exc.reason}") from exc

        choices = data.get("choices")
        if not choices:
            raise RuntimeError(f"OpenRouter {self.model_name} returned no choices: {data}")
        message = choices[0].get("message") or {}
        return (message.get("content") or "").strip()


class NvidiaChatLLM:
    def __init__(
        self,
        api_key: str | None,
        model_name: str,
        base_url: str = "https://integrate.api.nvidia.com/v1",
    ):
        if not api_key:
            raise RuntimeError("NVIDIA_KEY, NVIDIA_API_KEY, or NVIDIA_NIM_API_KEY is required for NVIDIA generation.")
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")

    def generate(self, system: str, user: str, max_new_tokens: int = 512) -> str:
        return self.generate_with_images(system, user, [], max_new_tokens)

    def generate_with_images(
        self,
        system: str,
        user: str,
        image_paths: list[Path],
        max_new_tokens: int = 512,
    ) -> str:
        content = user
        for image_path in image_paths:
            content += f'\n\n<img src="{_image_data_url(image_path)}" />'
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            "temperature": 0,
            "max_tokens": max_new_tokens,
        }
        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        NVIDIA_RATE_LIMITER.wait()
        try:
            with request.urlopen(req, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"NVIDIA {self.model_name} request failed with HTTP {exc.code}: {body}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(f"NVIDIA {self.model_name} request failed: {exc.reason}") from exc

        choices = data.get("choices")
        if not choices:
            raise RuntimeError(f"NVIDIA {self.model_name} returned no choices: {data}")
        message = choices[0].get("message") or {}
        return (message.get("content") or "").strip()


class GeminiChatLLM:
    def __init__(self, api_key: str | list[str] | tuple[str, ...] | None, model_name: str):
        api_keys = _normalize_keys(api_key)
        if not api_keys:
            raise RuntimeError("GEMINI_1..GEMINI_6, GEMINI_API_KEY, or GOOGLE_API_KEY is required for Gemini.")
        self.api_keys = api_keys
        self._next_key = 0
        self.model_name = model_name

    def generate(self, system: str, user: str, max_new_tokens: int = 512) -> str:
        return self._generate(system, user, [], max_new_tokens, json_mode=True)

    def generate_with_images(
        self,
        system: str,
        user: str,
        image_paths: list[Path],
        max_new_tokens: int = 512,
    ) -> str:
        return self._generate(system, user, image_paths, max_new_tokens, json_mode=False)

    def _generate(
        self,
        system: str,
        user: str,
        image_paths: list[Path],
        max_new_tokens: int,
        *,
        json_mode: bool,
    ) -> str:
        errors: list[str] = []
        for _ in range(len(self.api_keys)):
            api_key = self._next_api_key()
            try:
                return self._generate_once(
                    api_key=api_key,
                    system=system,
                    user=user,
                    image_paths=image_paths,
                    max_new_tokens=max_new_tokens,
                    json_mode=json_mode,
                )
            except HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                errors.append(f"HTTP {exc.code}: {body}")
            except (URLError, TimeoutError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
        raise RuntimeError(
            f"All configured Gemini API keys failed for {self.model_name}. " + " | ".join(errors)
        )

    def _next_api_key(self) -> str:
        api_key = self.api_keys[self._next_key]
        self._next_key = (self._next_key + 1) % len(self.api_keys)
        return api_key

    def _generate_once(
        self,
        *,
        api_key: str,
        system: str,
        user: str,
        image_paths: list[Path],
        max_new_tokens: int,
        json_mode: bool,
    ) -> str:
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{parse.quote(self.model_name, safe='')}:generateContent"
            f"?key={parse.quote(api_key, safe='')}"
        )
        parts = [{"text": user}]
        for image_path in image_paths:
            parts.append(_gemini_image_part(image_path))
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": max_new_tokens,
            },
        }
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"
        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0].get("text", "").strip()


class FallbackChatLLM:
    def __init__(self, primary: ChatLLM, fallback: ChatLLM):
        self.primary = primary
        self.fallback = fallback

    def generate(self, system: str, user: str, max_new_tokens: int = 512) -> str:
        try:
            return self.primary.generate(system, user, max_new_tokens)
        except Exception as exc:
            print(f"Chunking primary LLM failed; using fallback. Reason: {type(exc).__name__}: {exc}", flush=True)
            return self.fallback.generate(system, user, max_new_tokens)

    def generate_with_images(
        self,
        system: str,
        user: str,
        image_paths: list[Path],
        max_new_tokens: int = 512,
    ) -> str:
        try:
            return self.primary.generate_with_images(system, user, image_paths, max_new_tokens)
        except Exception as exc:
            print(f"Primary VLM failed; using fallback. Reason: {type(exc).__name__}: {exc}", flush=True)
            return self.fallback.generate_with_images(system, user, image_paths, max_new_tokens)


class PropositionChunker:
    def __init__(self, llm: ChatLLM):
        self.llm = llm

    def chunk(self, page_text: str, table_markdown: str, doc_type: str, section: str, context: str) -> list[str]:
        source = "\n\n".join(part for part in [page_text, table_markdown] if part.strip())
        if not source.strip():
            return []
        user = f"""
Convert the source into atomic factual propositions for retrieval.
Preserve exact numbers, units, row-column relationships, periods, qualifiers, and exceptions.
Do not infer facts. Return only a JSON array of strings.

Document type: {doc_type}
Section: {section}
Context: {context}

SOURCE:
{source}
""".strip()
        raw = ""
        parsed = None
        for max_new_tokens in (4096, 8192):
            raw = self.llm.generate(
                system="You produce faithful JSON only. No markdown fences.",
                user=user,
                max_new_tokens=max_new_tokens,
            )
            try:
                parsed = json.loads(_extract_json_array(raw))
                break
            except json.JSONDecodeError:
                parsed = None
        if parsed is None:
            raise RuntimeError(f"Proposition chunking did not return valid JSON: {raw[:500]}")
        if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
            raise RuntimeError("Proposition chunking must return a JSON array of strings.")
        return [item.strip() for item in parsed if item.strip()]


def _extract_json_array(text: str) -> str:
    clean = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", clean, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        clean = fenced.group(1).strip()
    if clean.startswith("["):
        return clean
    start = clean.find("[")
    end = clean.rfind("]")
    if start >= 0 and end > start:
        return clean[start : end + 1]
    return clean


def _image_data_url(image_path: Path, target_bytes: int = 8_000) -> str:
    with Image.open(image_path) as image:
        image = image.convert("RGB")
        max_side = 1200
        quality = 80
        while True:
            candidate = _resize_image_to_max_side(image, max_side)
            buffer = BytesIO()
            candidate.save(buffer, format="JPEG", quality=quality, optimize=True)
            data = buffer.getvalue()
            if len(data) <= target_bytes or max_side <= 700:
                break
            max_side = int(max_side * 0.85)
            quality = max(60, quality - 5)
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _gemini_image_part(image_path: Path, target_bytes: int = 1_000_000) -> dict:
    with Image.open(image_path) as image:
        image = image.convert("RGB")
        max_side = 1400
        quality = 85
        while True:
            candidate = _resize_image_to_max_side(image, max_side)
            buffer = BytesIO()
            candidate.save(buffer, format="JPEG", quality=quality, optimize=True)
            data = buffer.getvalue()
            if len(data) <= target_bytes or max_side <= 800:
                break
            max_side = int(max_side * 0.85)
            quality = max(65, quality - 5)
    return {
        "inline_data": {
            "mime_type": "image/jpeg",
            "data": base64.b64encode(data).decode("ascii"),
        }
    }


def _normalize_keys(api_key: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if api_key is None:
        candidates: list[str | None] = []
    elif isinstance(api_key, str):
        candidates = [api_key]
    else:
        candidates = list(api_key)
    keys: list[str] = []
    for candidate in candidates:
        value = (candidate or "").strip().strip('"')
        if value and value not in keys:
            keys.append(value)
    return keys


def _resize_image_to_max_side(image: Image.Image, max_side: int) -> Image.Image:
    width, height = image.size
    longest = max(width, height)
    if longest <= max_side:
        return image
    scale = max_side / longest
    size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)
