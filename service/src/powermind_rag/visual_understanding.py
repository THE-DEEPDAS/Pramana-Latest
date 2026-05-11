from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path
from urllib import request
from urllib.error import HTTPError, URLError

from PIL import Image

from powermind_rag.llm import GeminiChatLLM, LocalQwenVL
from powermind_rag.rate_limit import NVIDIA_RATE_LIMITER


class NvidiaVisualPageAnalyzer:
    def __init__(
        self,
        api_key: str | None,
        model_name: str,
        base_url: str,
        max_tokens: int = 4096,
        image_max_bytes: int = 100_000,
        image_max_side: int = 1400,
        timeout_seconds: int = 600,
    ):
        if not api_key:
            raise RuntimeError(
                "NVIDIA_API_KEY or NVIDIA_NIM_API_KEY is required when "
                "POWERMIND_ENABLE_VISUAL_UNDERSTANDING=true."
            )
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.max_tokens = max_tokens
        self.image_max_bytes = image_max_bytes
        self.image_max_side = image_max_side
        self.timeout_seconds = timeout_seconds

    def analyze_page(
        self,
        image_path: Path,
        page_number: int,
        doc_type: str,
        section: str,
        context: str,
    ) -> str:
        image_data_url = _image_data_url(
            image_path,
            target_bytes=self.image_max_bytes,
            initial_max_side=self.image_max_side,
        )
        prompt = _analysis_prompt(
            page_number=page_number,
            doc_type=doc_type,
            section=section,
            context=context,
        )
        payload = {
            "model": self.model_name,
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a precise document intelligence extractor. "
                        "Read the page image only. Preserve visible text, numbers, labels, units, "
                        "periods, and table relationships. "
                        "Extract all numeric and text data from charts and infographics exactly as shown. "
                        "Do not infer missing values."
                    ),
                },
                {
                    "role": "user",
                    "content": f'{prompt}\n\n<img src="{image_data_url}" />',
                },
            ],
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
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"NVIDIA VLM {self.model_name} request failed with HTTP {exc.code}: {body}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(f"NVIDIA VLM {self.model_name} request failed: {exc.reason}") from exc

        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"NVIDIA VLM {self.model_name} returned no choices: {data}")
        message = choices[0].get("message") or {}
        content = (message.get("content") or "").strip()
        if not content:
            raise RuntimeError(f"NVIDIA VLM {self.model_name} returned an empty page analysis.")
        return content


class GeminiVisualPageAnalyzer:
    def __init__(
        self,
        api_keys: tuple[str, ...] | list[str],
        model_name: str,
        fallback: NvidiaVisualPageAnalyzer | None = None,
        max_tokens: int = 4096,
    ):
        self.llm = GeminiChatLLM(api_key=api_keys, model_name=model_name)
        self.model_name = model_name
        self.fallback = fallback
        self.max_tokens = max_tokens

    def analyze_page(
        self,
        image_path: Path,
        page_number: int,
        doc_type: str,
        section: str,
        context: str,
    ) -> str:
        prompt = _analysis_prompt(
            page_number=page_number,
            doc_type=doc_type,
            section=section,
            context=context,
        )
        try:
            content = self.llm.generate_with_images(
                system=_strict_visual_system_prompt(),
                user=prompt,
                image_paths=[image_path.resolve()],
                max_new_tokens=self.max_tokens,
            ).strip()
            if content:
                return content
            raise RuntimeError(f"Gemini {self.model_name} returned an empty page analysis.")
        except Exception as exc:
            if self.fallback is None:
                raise
            print(
                f"Gemini VLM exhausted/failed for page {page_number}; using NVIDIA Phi fallback. "
                f"Reason: {type(exc).__name__}: {exc}",
                flush=True,
            )
            return self.fallback.analyze_page(
                image_path=image_path,
                page_number=page_number,
                doc_type=doc_type,
                section=section,
                context=context,
            )


class NvidiaFirstVisualPageAnalyzer:
    def __init__(
        self,
        primary: NvidiaVisualPageAnalyzer,
        fallback: GeminiVisualPageAnalyzer,
    ):
        self.primary = primary
        self.fallback = fallback

    def analyze_page(
        self,
        image_path: Path,
        page_number: int,
        doc_type: str,
        section: str,
        context: str,
    ) -> str:
        try:
            return self.primary.analyze_page(
                image_path=image_path,
                page_number=page_number,
                doc_type=doc_type,
                section=section,
                context=context,
            )
        except Exception as exc:
            print(
                f"NVIDIA VLM failed for page {page_number}; using Gemini fallback. "
                f"Reason: {type(exc).__name__}: {exc}",
                flush=True,
            )
            return self.fallback.analyze_page(
                image_path=image_path,
                page_number=page_number,
                doc_type=doc_type,
                section=section,
                context=context,
            )


class LocalQwenVLVisualPageAnalyzer:
    def __init__(
        self,
        model_path: Path,
        device: str,
        max_tokens: int = 4096,
    ):
        self.max_tokens = max_tokens
        self.llm = LocalQwenVL(model_path, device=device)

    def analyze_page(
        self,
        image_path: Path,
        page_number: int,
        doc_type: str,
        section: str,
        context: str,
    ) -> str:
        prompt = _analysis_prompt(
            page_number=page_number,
            doc_type=doc_type,
            section=section,
            context=context,
        )
        content = self.llm.generate_with_images(
            system=(
                _strict_visual_system_prompt()
            ),
            user=prompt,
            image_paths=[image_path.resolve()],
            max_new_tokens=self.max_tokens,
        ).strip()
        if not content:
            raise RuntimeError("Local Qwen-VL returned an empty page analysis.")
        return content

    def unload_model(self) -> None:
        self.llm.unload_model()


def _analysis_prompt(page_number: int, doc_type: str, section: str, context: str) -> str:
    return f"""
Analyze page {page_number} of this document image for retrieval.

Document type: {doc_type}
Section: {section}
Context: {context}

Return markdown only, with exactly these sections:

## Page Summary
- Briefly explain what this page is about.

## OCR Text
- Extract all readable normal text from the page.

## Visual, Chart, And Infographic Data
- Explain charts, graphs, maps, flowcharts, icons, callouts, legends, color labels, arrows, and layout relationships.
- Extract all text embedded inside diagrams, shapes, banners, badges, callouts, arrows, axis ticks, legends, and data labels.
- Convert visible chart or infographic values into text with exact labels, numbers, units, periods, directions, and comparisons.

## Tables
- Recreate every visible table as a valid markdown table.
- Preserve row and column headers, units, footnotes, totals, percentages, currency symbols, and comparison periods.
- If there is no table, write: No table detected.

Rules:
- Do not use outside knowledge.
- Do not calculate values unless the page explicitly shows the calculation.
- If text is unreadable, write [unclear] rather than guessing.
- Keep the result factual and dense for search retrieval.
""".strip()


def _strict_visual_system_prompt() -> str:
    return (
        "You are a precise document intelligence extractor. "
        "Read the page image only. Preserve visible text, numbers, labels, units, "
        "periods, and table relationships exactly as visible. "
        "Extract all numeric and text data from charts, tables, diagrams, footnotes, "
        "infographics, axes, legends, icons, and callouts. "
        "Do not infer missing values, round numbers, normalize formatting, or use outside knowledge."
    )


def _image_data_url(image_path: Path, target_bytes: int, initial_max_side: int) -> str:
    with Image.open(image_path) as image:
        image = image.convert("RGB")
        encoded = _encode_jpeg_under_limit(
            image,
            target_bytes=target_bytes,
            initial_max_side=initial_max_side,
        )
    return f"data:image/jpeg;base64,{base64.b64encode(encoded).decode('ascii')}"


def _encode_jpeg_under_limit(
    image: Image.Image,
    target_bytes: int,
    initial_max_side: int,
) -> bytes:
    resized = image
    max_side = initial_max_side
    quality = 85
    while True:
        candidate = _resize_to_max_side(resized, max_side)
        buffer = BytesIO()
        candidate.save(buffer, format="JPEG", quality=quality, optimize=True)
        data = buffer.getvalue()
        if len(data) <= target_bytes or max_side <= 900:
            return data
        max_side = int(max_side * 0.85)
        quality = max(65, quality - 5)


def _resize_to_max_side(image: Image.Image, max_side: int) -> Image.Image:
    width, height = image.size
    longest = max(width, height)
    if longest <= max_side:
        return image
    scale = max_side / longest
    size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)
