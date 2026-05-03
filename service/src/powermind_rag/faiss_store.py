from __future__ import annotations

import json
from pathlib import Path
from typing import Generic, TypeVar

import faiss
import numpy as np

T = TypeVar("T")


class FaissStore(Generic[T]):
    def __init__(self, dimension: int, metric: str = "cosine"):
        if metric != "cosine":
            raise ValueError("Only cosine similarity is supported; vectors must be normalized.")
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.records: list[T] = []

    def add(self, vectors: np.ndarray, records: list[T]) -> None:
        if vectors.ndim != 2 or vectors.shape[1] != self.dimension:
            raise ValueError(f"Expected vectors with shape (*, {self.dimension}), got {vectors.shape}.")
        if len(vectors) != len(records):
            raise ValueError("Vector and record counts differ.")
        self.index.add(np.asarray(vectors, dtype="float32"))
        self.records.extend(records)

    def search(self, query_vector: np.ndarray, top_k: int) -> list[tuple[T, float, int]]:
        vector = np.asarray(query_vector, dtype="float32")
        if vector.ndim == 1:
            vector = vector.reshape(1, -1)
        scores, ids = self.index.search(vector, top_k)
        hits: list[tuple[T, float, int]] = []
        for rank, (idx, score) in enumerate(zip(ids[0], scores[0]), start=1):
            if idx < 0:
                continue
            hits.append((self.records[int(idx)], float(score), rank))
        return hits

    def save(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(path / "index.faiss"))
        (path / "records.json").write_text(json.dumps(self.records, default=str, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path, records: list[T], dimension: int) -> "FaissStore[T]":
        store = cls(dimension)
        store.index = faiss.read_index(str(path / "index.faiss"))
        store.records = records
        return store
