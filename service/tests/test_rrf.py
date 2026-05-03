from powermind_rag.rrf import reciprocal_rank_fusion
from powermind_rag.schema import RetrievedChunk


def chunk(chunk_id: str, rank: int) -> RetrievedChunk:
    return RetrievedChunk(
        id=chunk_id,
        text=chunk_id,
        document_id="doc",
        page_number=1,
        modality="text",
        rank=rank,
        score=0.0,
    )


def test_rrf_uses_reciprocal_rank_without_score_normalization():
    fused = reciprocal_rank_fusion(
        [
            [chunk("a", 1), chunk("b", 2)],
            [chunk("b", 1), chunk("a", 2)],
        ],
        k=60,
    )

    assert [item.id for item in fused] == ["a", "b"]
    assert fused[0].score == (1 / 61) + (1 / 62)
    assert fused[1].score == (1 / 62) + (1 / 61)
