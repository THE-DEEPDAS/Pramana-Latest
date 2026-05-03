from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


Modality = Literal["text", "image"]


@dataclass(frozen=True)
class VisualPageRecord:
    embedding: list[float]
    document_id: str
    page_number: int
    modality: Literal["image"]
    raw_image_path: Path
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TextChunkRecord:
    text: str
    embedding: list[float]
    chunk_id: str
    document_id: str
    page_number: int
    modality: Literal["text"]
    context_prefix: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    text: str
    document_id: str
    page_number: int
    modality: Modality
    rank: int
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def citation(self) -> str:
        chunk_label = self.metadata.get("chunk_label", self.id)
        return f"[p{self.page_number}:{chunk_label}]"


@dataclass(frozen=True)
class Answer:
    text: str
    retrieved: list[RetrievedChunk]
    is_fallback: bool = False
    verifier_report: dict[str, Any] = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)
