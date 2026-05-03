from __future__ import annotations

from collections import defaultdict

from powermind_rag.schema import RetrievedChunk


def reciprocal_rank_fusion(rankings: list[list[RetrievedChunk]], k: int = 60) -> list[RetrievedChunk]:
    scores: dict[str, float] = defaultdict(float)
    best: dict[str, RetrievedChunk] = {}
    for ranking in rankings:
        for rank, chunk in enumerate(ranking, start=1):
            scores[chunk.id] += 1.0 / (k + rank)
            best.setdefault(chunk.id, chunk)
    fused = sorted(best.values(), key=lambda chunk: scores[chunk.id], reverse=True)
    return [
        RetrievedChunk(
            id=chunk.id,
            text=chunk.text,
            document_id=chunk.document_id,
            page_number=chunk.page_number,
            modality=chunk.modality,
            rank=rank,
            score=scores[chunk.id],
            metadata=chunk.metadata,
        )
        for rank, chunk in enumerate(fused, start=1)
    ]
