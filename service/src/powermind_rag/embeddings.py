from __future__ import annotations

from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer


class DenseEmbedder:
    def __init__(self, model_name: str, device: str):
        self.model_name = model_name
        self.device = device
        self._direct_e5 = _is_e5_model(model_name)
        if self._direct_e5:
            model_path = _resolve_local_model_path(model_name)
            self.tokenizer = AutoTokenizer.from_pretrained(str(model_path))
            self.model = AutoModel.from_pretrained(str(model_path)).to(device)
            self.model.eval()
        else:
            self.model = SentenceTransformer(model_name, device=device)

    def encode(self, texts: list[str]) -> np.ndarray:
        return self.encode_passages(texts)

    def encode_passages(self, texts: list[str]) -> np.ndarray:
        prepared = self._prepare(texts, prefix="passage")
        if self._direct_e5:
            return self._encode_transformer(prepared)
        vectors = self.model.encode(
            prepared,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype="float32")

    def encode_queries(self, texts: list[str]) -> np.ndarray:
        prepared = self._prepare(texts, prefix="query")
        if self._direct_e5:
            return self._encode_transformer(prepared)
        vectors = self.model.encode(
            prepared,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype="float32")

    @property
    def dimension(self) -> int:
        return int(self.encode(["dimension probe"]).shape[1])

    def _prepare(self, texts: list[str], prefix: str) -> list[str]:
        if not _is_e5_model(self.model_name):
            return texts
        return [f"{prefix}: {text}" for text in texts]

    def _encode_transformer(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        vectors = []
        with torch.inference_mode():
            for start in range(0, len(texts), batch_size):
                batch = texts[start : start + batch_size]
                encoded = self.tokenizer(
                    batch,
                    max_length=512,
                    padding=True,
                    truncation=True,
                    return_tensors="pt",
                ).to(self.device)
                outputs = self.model(**encoded)
                pooled = _average_pool(outputs.last_hidden_state, encoded["attention_mask"])
                normalized = F.normalize(pooled, p=2, dim=1)
                vectors.append(normalized.detach().cpu().numpy())
        return np.asarray(np.vstack(vectors), dtype="float32")


def _is_e5_model(model_name: str) -> bool:
    return "e5" in model_name.lower()


def _average_pool(last_hidden_states: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    masked = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
    return masked.sum(dim=1) / attention_mask.sum(dim=1)[..., None]


def _resolve_local_model_path(model_name: str) -> Path:
    path = Path(model_name)
    if path.exists():
        return path
    repo_root_path = Path(__file__).resolve().parents[3] / model_name
    if repo_root_path.exists():
        return repo_root_path
    return path
