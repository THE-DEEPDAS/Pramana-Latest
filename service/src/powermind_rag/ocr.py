from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from pathlib import Path

try:
    from mistralai.client import Mistral
except ImportError:  # pragma: no cover - compatibility with older mistralai layouts
    from mistralai import Mistral


@dataclass(frozen=True)
class OCRTable:
    page_number: int
    markdown: str


class MistralTableOCR:
    def __init__(
        self,
        api_key: str | None,
        model: str,
        server_url: str = "https://api.mistral.ai",
        timeout_ms: int = 120_000,
        max_attempts: int = 3,
    ):
        if not api_key:
            raise RuntimeError("MISTRAL_API_KEY is required for table OCR.")
        self.client = Mistral(api_key=api_key, server_url=server_url, timeout_ms=timeout_ms)
        self.model = model
        self.max_attempts = max_attempts

    def extract_markdown_tables(self, image_paths: list[Path]) -> list[OCRTable]:
        tables: list[OCRTable] = []
        for page_number, path in enumerate(image_paths, start=1):
            image_b64 = base64.b64encode(path.read_bytes()).decode("ascii")
            response = self._process_with_retries(image_b64)
            markdown_parts: list[str] = []
            for page in getattr(response, "pages", []):
                for table in getattr(page, "tables", []) or []:
                    markdown_parts.append(getattr(table, "markdown", None) or getattr(table, "content", ""))
                markdown_parts.append(getattr(page, "markdown", ""))
            markdown = "\n\n".join(part for part in markdown_parts if part)
            table_blocks = self._table_blocks(markdown)
            content = "\n\n".join(table_blocks) if table_blocks else markdown
            if content.strip():
                tables.append(OCRTable(page_number=page_number, markdown=content.strip()))
        return tables

    def _process_with_retries(self, image_b64: str):
        last_exc: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self.client.ocr.process(
                    model=self.model,
                    document={
                        "type": "image_url",
                        "image_url": f"data:image/png;base64,{image_b64}",
                    },
                    table_format="markdown",
                )
            except Exception as exc:
                last_exc = exc
                if attempt >= self.max_attempts:
                    break
                time.sleep(2 * attempt)
        raise RuntimeError(f"Mistral OCR failed after {self.max_attempts} attempts.") from last_exc

    @staticmethod
    def _table_blocks(markdown: str) -> list[str]:
        blocks: list[str] = []
        current: list[str] = []
        for line in markdown.splitlines():
            is_table_line = line.strip().startswith("|") and line.strip().endswith("|")
            if is_table_line:
                current.append(line)
            elif current:
                if len(current) >= 2:
                    blocks.append("\n".join(current))
                current = []
        if len(current) >= 2:
            blocks.append("\n".join(current))
        return blocks
