from __future__ import annotations

from pathlib import Path

from powermind_rag.pipeline import MAX_IMAGE_FALLBACK_PAGES, MultimodalRAGPipeline, NOT_FOUND
from powermind_rag.schema import RetrievedChunk


class DummyImageLLM:
    def __init__(self):
        self.calls = []

    def generate(self, system: str, user: str, max_new_tokens: int = 512) -> str:
        self.calls.append(
            {
                "mode": "text",
                "system": system,
                "user": user,
                "images": [],
                "max_new_tokens": max_new_tokens,
            }
        )
        return "Recovered answer"

    def generate_with_images(
        self,
        system: str,
        user: str,
        image_paths: list,
        max_new_tokens: int = 512,
    ) -> str:
        self.calls.append(
            {
                "mode": "images",
                "system": system,
                "user": user,
                "images": [str(path) for path in image_paths],
                "max_new_tokens": max_new_tokens,
            }
        )
        return "Recovered answer"


def _chunk(chunk_id: str, rank: int, *, modality: str = "text", raw_image_path: str | None = None) -> RetrievedChunk:
    metadata = {}
    if raw_image_path is not None:
        metadata["raw_image_path"] = raw_image_path
    return RetrievedChunk(
        id=chunk_id,
        text=f"{chunk_id} body",
        document_id="doc",
        page_number=rank,
        modality=modality,
        rank=rank,
        score=1.0 / rank,
        metadata=metadata,
    )


def test_generate_image_fallback_uses_only_top_three_chunks_and_attaches_images(tmp_path: Path):
    pipeline = object.__new__(MultimodalRAGPipeline)
    dummy_llm = DummyImageLLM()
    pipeline._image_llm = lambda: dummy_llm
    pipeline.config = type("Config", (), {"storage_dir": tmp_path})()

    storage_root = tmp_path
    (storage_root / "doc" / "pages").mkdir(parents=True, exist_ok=True)
    (storage_root / "doc" / "pages" / "page_0001.png").write_bytes(b"page-1")
    (storage_root / "doc" / "pages" / "page_0002.png").write_bytes(b"page-2")
    (storage_root / "doc" / "pages" / "page_0003.png").write_bytes(b"page-3")

    chunks = [
        _chunk("c1", 1),
        _chunk("c2", 2),
        _chunk("c3", 3),
        _chunk("c4", 4),
    ]

    answer = pipeline._generate_image_fallback("What is the answer?", chunks)

    assert answer == "Recovered answer"
    assert len(dummy_llm.calls) == 1
    call = dummy_llm.calls[0]
    assert call["mode"] == "images"
    assert [path.replace("\\", "/") for path in call["images"]] == [
        str(tmp_path / "doc" / "pages" / "page_0001.png").replace("\\", "/"),
        str(tmp_path / "doc" / "pages" / "page_0002.png").replace("\\", "/"),
        str(tmp_path / "doc" / "pages" / "page_0003.png").replace("\\", "/"),
    ]
    assert "c1 body" not in call["user"]
    assert "c2 body" not in call["user"]
    assert "c3 body" not in call["user"]
    assert "c4 body" not in call["user"]
    assert "retrieved chunks" not in call["user"].lower()
    assert NOT_FOUND in call["user"]
    assert MAX_IMAGE_FALLBACK_PAGES == 3
