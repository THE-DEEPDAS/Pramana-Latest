from __future__ import annotations

import json
import re
from urllib.error import HTTPError
from pathlib import Path
from typing import Protocol
from urllib import parse, request

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


class ChatLLM(Protocol):
    def generate(self, system: str, user: str, max_new_tokens: int = 512) -> str:
        ...


class LocalQwen:
    def __init__(self, model_path: Path, device: str):
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


class GeminiChatLLM:
    def __init__(self, api_key: str | None, model_name: str):
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY_2, GEMINI_API_KEY, or GOOGLE_API_KEY is required for Gemini chunking.")
        self.api_key = api_key
        self.model_name = model_name

    def generate(self, system: str, user: str, max_new_tokens: int = 512) -> str:
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{parse.quote(self.model_name, safe='')}:generateContent"
            f"?key={parse.quote(self.api_key, safe='')}"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": max_new_tokens,
                "responseMimeType": "application/json",
            },
        }
        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini {self.model_name} request failed with HTTP {exc.code}: {body}") from exc
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
