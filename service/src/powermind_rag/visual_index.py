from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from powermind_rag.faiss_store import FaissStore
from powermind_rag.schema import RetrievedChunk, VisualPageRecord


class ColPaliVisualIndex:
    """ColPali/byaldi page-level index plus FAISS storage for pooled page embeddings."""

    def __init__(self, model_name: str, device: str):
        try:
            from byaldi import RAGMultiModalModel
        except ImportError as exc:
            raise RuntimeError("ColPali visual ingestion must use byaldi. Install byaldi.") from exc
        self.model_name = model_name
        self.device = device
        try:
            self.model = RAGMultiModalModel.from_pretrained(model_name, device=device)
        except TypeError:
            self.model = RAGMultiModalModel.from_pretrained(model_name)
            nested = getattr(self.model, "model", self.model)
            if hasattr(nested, "to"):
                nested.to(device)
        except Exception as exc:
            raise RuntimeError(
                "Failed to load the ColPali visual model. The visual index is required for the strict RAG architecture, "
                "so fix the ColPali/byaldi/peft/transformers environment before running queries."
            ) from exc
        self.records: list[VisualPageRecord] = []
        self.faiss: FaissStore[VisualPageRecord] | None = None

    def build(self, image_paths: list[Path], document_id: str, metadata: dict[str, Any]) -> None:
        image_paths = sorted(image_paths)
        self._build_byaldi_collection(image_paths, document_id, metadata)
        indexed_embeddings = self._indexed_page_embeddings()
        records: list[VisualPageRecord] = []
        vectors: list[np.ndarray] = []
        for page_number, image_path in enumerate(image_paths, start=1):
            embedding = indexed_embeddings.get(page_number)
            if embedding is None:
                embedding = self._embed_page(image_path)
            vectors.append(embedding)
            records.append(
                VisualPageRecord(
                    embedding=embedding.tolist(),
                    document_id=document_id,
                    page_number=page_number,
                    modality="image",
                    raw_image_path=image_path,
                    metadata=metadata,
                )
            )
        matrix = np.asarray(vectors, dtype="float32")
        self.faiss = FaissStore(dimension=matrix.shape[1])
        self.faiss.add(matrix, records)
        self.records.extend(records)

    def _build_byaldi_collection(
        self, image_paths: list[Path], document_id: str, metadata: dict[str, Any]
    ) -> None:
        index_method = getattr(self.model, "index", None)
        if index_method is None:
            return
        self._reset_byaldi_state()
        doc_ids = list(range(1, len(image_paths) + 1))
        page_metadata = {
            page_number: {**metadata, "document_id": document_id, "page_number": page_number}
            for page_number in doc_ids
        }
        try:
            index_method(
                input_path=str(image_paths[0].parent),
                index_name=f"{document_id}_visual",
                doc_ids=doc_ids,
                store_collection_with_index=True,
                overwrite=True,
                metadata=page_metadata,
            )
        except TypeError:
            index_method(str(image_paths[0].parent), index_name=f"{document_id}_visual", overwrite=True)

    def _reset_byaldi_state(self) -> None:
        nested = getattr(self.model, "model", self.model)
        if hasattr(nested, "index_name"):
            nested.index_name = None
        if hasattr(nested, "collection"):
            nested.collection = {}
        if hasattr(nested, "indexed_embeddings"):
            nested.indexed_embeddings = []
        if hasattr(nested, "embed_id_to_doc_id"):
            nested.embed_id_to_doc_id = {}
        if hasattr(nested, "doc_id_to_metadata"):
            nested.doc_id_to_metadata = {}
        if hasattr(nested, "doc_ids_to_file_names"):
            nested.doc_ids_to_file_names = {}
        if hasattr(nested, "doc_ids"):
            nested.doc_ids = set()
        if hasattr(nested, "highest_doc_id"):
            nested.highest_doc_id = -1

    def search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        if not self.records and self.faiss is None:
            return []
        byaldi_hits = self._byaldi_search(query, top_k)
        if byaldi_hits:
            return byaldi_hits
        if self.faiss is None:
            raise RuntimeError("Visual FAISS index has not been built.")
        query_vector = self._embed_query(query)
        return [
            self._to_retrieved(record, rank, score)
            for record, score, rank in self.faiss.search(query_vector, top_k)
        ]

    def _byaldi_search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        if not hasattr(self.model, "search"):
            return []
        try:
            hits = self.model.search(query, k=top_k)
        except (TypeError, ValueError):
            return []
        retrieved: list[RetrievedChunk] = []
        for rank, hit in enumerate(hits, start=1):
            metadata = getattr(hit, "metadata", {}) or {}
            page_number = int(
                metadata.get("page_number")
                or getattr(hit, "page_num", getattr(hit, "page_number", 0))
                or getattr(hit, "doc_id", 0)
                or 0
            )
            score = float(getattr(hit, "score", 0.0))
            hit_doc = metadata.get("document_id") or getattr(hit, "document_id", None)
            candidates = [item for item in self.records if item.page_number == page_number]
            if hit_doc:
                candidates = [item for item in candidates if item.document_id == str(hit_doc)]
            if len(candidates) != 1:
                return []
            record = candidates[0]
            if not record:
                continue
            retrieved.append(self._to_retrieved(record, rank, score))
        return retrieved

    def _embed_page(self, image_path: Path) -> np.ndarray:
        import torch
        image = Image.open(image_path).convert("RGB")

        nested = getattr(self.model, "model", self.model)
        if nested is not None and hasattr(nested, "encode_image"):
            try:
                with torch.no_grad():
                    raw = nested.encode_image(image)
                return self._pool_normalize(raw)
            except Exception:
                pass

        for method_name in ("encode_images", "embed_images", "embed_image"):
            method = getattr(nested, method_name, None) or getattr(self.model, method_name, None)
            if method is None:
                continue
            try:
                with torch.no_grad():
                    raw = method([image]) if method_name.endswith("s") else method(image)
                return self._pool_normalize(raw)
            except Exception:
                continue
        raise RuntimeError("Unable to obtain page-level ColPali embeddings from byaldi model.")

    def _embed_query(self, query: str) -> np.ndarray:
        nested = getattr(self.model, "model", self.model)
        for method_name in ("encode_queries", "encode_query", "embed_queries", "embed_query"):
            method = getattr(nested, method_name, None) or getattr(self.model, method_name, None)
            if method is None:
                continue
            try:
                raw = method([query]) if method_name.endswith("s") else method(query)
                return self._pool_normalize(raw)
            except Exception:
                continue
        raise RuntimeError("Unable to obtain ColPali query embedding from byaldi model.")

    def _indexed_page_embeddings(self) -> dict[int, np.ndarray]:
        nested = getattr(self.model, "model", self.model)
        indexed = getattr(nested, "indexed_embeddings", None)
        mapping = getattr(nested, "embed_id_to_doc_id", None)
        if not indexed or not mapping:
            return {}
        page_embeddings: dict[int, np.ndarray] = {}
        for embed_id, doc_info in mapping.items():
            if int(embed_id) >= len(indexed):
                continue
            page_number = int(doc_info.get("doc_id") or doc_info.get("page_id") or 0)
            if page_number <= 0:
                continue
            page_embeddings[page_number] = self._pool_normalize(indexed[int(embed_id)])
        return page_embeddings

    @staticmethod
    def _pool_normalize(raw: Any) -> np.ndarray:
        if hasattr(raw, "detach"):
            raw = raw.detach().float().cpu().numpy()
        array = np.asarray(raw, dtype="float32")
        while array.ndim > 1:
            array = array.mean(axis=0)
        norm = np.linalg.norm(array)
        if norm == 0:
            raise RuntimeError("ColPali produced a zero vector.")
        return array / norm

    @staticmethod
    def _to_retrieved(record: VisualPageRecord, rank: int, score: float) -> RetrievedChunk:
        return RetrievedChunk(
            id=f"{record.document_id}:p{record.page_number}:image",
            text=(
                f"Visual page evidence only. Source image: {record.raw_image_path}. "
                "Do not extract numeric values unless separate textual evidence supports them."
            ),
            document_id=record.document_id,
            page_number=record.page_number,
            modality="image",
            rank=rank,
            score=score,
            metadata={
                **record.metadata,
                "chunk_label": "image",
                "raw_image_path": str(record.raw_image_path),
            },
        )

    def save_records(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(record) for record in self.records]
        path.write_text(json.dumps(payload, default=str, indent=2), encoding="utf-8")

    def save_document_records(self, document_id: str, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [asdict(record) for record in self.records if record.document_id == document_id]
        path.write_text(json.dumps(payload, default=str, indent=2), encoding="utf-8")

    def load_records(self, records: list[VisualPageRecord]) -> None:
        self.records = records
        if not records:
            return
        matrix = np.asarray([record.embedding for record in records], dtype="float32")
        self.faiss = FaissStore(dimension=matrix.shape[1])
        self.faiss.add(matrix, records)


def load_visual_records(path: Path) -> list[VisualPageRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records: list[VisualPageRecord] = []
    for item in payload:
        item["raw_image_path"] = Path(item["raw_image_path"])
        records.append(VisualPageRecord(**item))
    return records
