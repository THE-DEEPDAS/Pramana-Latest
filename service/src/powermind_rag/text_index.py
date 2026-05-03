from __future__ import annotations

import re
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from powermind_rag.embeddings import DenseEmbedder
from powermind_rag.faiss_store import FaissStore
from powermind_rag.schema import RetrievedChunk, TextChunkRecord


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9.,%/-]+", text.lower())


class HybridTextIndex:
    def __init__(self, embedder: DenseEmbedder):
        self.embedder = embedder
        self.records: list[TextChunkRecord] = []
        self.bm25: BM25Okapi | None = None
        self.faiss: FaissStore[TextChunkRecord] | None = None

    def build(self, records: list[TextChunkRecord]) -> None:
        self.records = records
        self.bm25 = BM25Okapi([tokenize(record.text) for record in records])
        vectors = np.asarray([record.embedding for record in records], dtype="float32")
        self.faiss = FaissStore(dimension=vectors.shape[1])
        self.faiss.add(vectors, records)

    def bm25_search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        if self.bm25 is None:
            raise RuntimeError("BM25 index has not been built.")
        scores = self.bm25.get_scores(tokenize(query))
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)[:top_k]
        return [self._to_retrieved(self.records[idx], rank + 1, float(score)) for rank, (idx, score) in enumerate(ranked)]

    def dense_search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        if self.faiss is None:
            raise RuntimeError("Dense FAISS text index has not been built.")
        query_vector = self.embedder.encode_queries([query])[0]
        return [
            self._to_retrieved(record, rank, score)
            for record, score, rank in self.faiss.search(query_vector, top_k)
        ]

    def keyword_search(self, terms: list[str], top_k: int) -> list[RetrievedChunk]:
        if not terms:
            return []
        normalized_terms = [term.lower() for term in terms if term.strip()]
        scored: list[tuple[int, float]] = []
        for idx, record in enumerate(self.records):
            text = record.text.lower()
            score = sum(1.0 for term in normalized_terms if term in text)
            if score:
                scored.append((idx, score))
        ranked = sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]
        return [self._to_retrieved(self.records[idx], rank + 1, score) for rank, (idx, score) in enumerate(ranked)]

    @staticmethod
    def _to_retrieved(record: TextChunkRecord, rank: int, score: float) -> RetrievedChunk:
        return RetrievedChunk(
            id=record.chunk_id,
            text=f"{record.context_prefix}\n{record.text}",
            document_id=record.document_id,
            page_number=record.page_number,
            modality="text",
            rank=rank,
            score=score,
            metadata=record.metadata,
        )

    def save_records(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(record) for record in self.records]
        path.write_text(json.dumps(payload, default=str, indent=2), encoding="utf-8")


def load_text_records(path: Path) -> list[TextChunkRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [TextChunkRecord(**item) for item in payload]


def save_text_records(records: list[TextChunkRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(record) for record in records]
    path.write_text(json.dumps(payload, default=str, indent=2), encoding="utf-8")
