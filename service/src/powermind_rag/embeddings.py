from __future__ import annotations

import json
from urllib import request
from urllib.error import HTTPError, URLError

import numpy as np

from powermind_rag.rate_limit import NVIDIA_RATE_LIMITER


class DenseEmbedder:
    """NVIDIA-hosted dense embedder.

    The class name is kept so the rest of the service does not need to care
    whether embeddings are local or remote. It now makes only NVIDIA API calls.
    """

    def __init__(
        self,
        model_name: str,
        device: str = "api",
        api_key: str | None = None,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        batch_size: int = 16,
        timeout_seconds: int = 120,
    ):
        if not api_key:
            raise RuntimeError(
                "NVIDIA_KEY, NVIDIA_API_KEY, or NVIDIA_NIM_API_KEY is required for embeddings."
            )
        self.model_name = model_name
        self.device = "nvidia-api"
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.batch_size = max(1, batch_size)
        self.timeout_seconds = timeout_seconds
        self._dimension: int | None = None

    def encode(self, texts: list[str]) -> np.ndarray:
        return self.encode_passages(texts)

    def encode_passages(self, texts: list[str]) -> np.ndarray:
        return self._embed(texts, input_type="passage")

    def encode_queries(self, texts: list[str]) -> np.ndarray:
        return self._embed(texts, input_type="query")

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            self._dimension = int(self.encode(["dimension probe"]).shape[1])
        return self._dimension

    def _embed(self, texts: list[str], input_type: str) -> np.ndarray:
        if not texts:
            return np.asarray([], dtype="float32")

        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            vectors.extend(self._embed_batch(batch, input_type=input_type))
        matrix = np.asarray(vectors, dtype="float32")
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        return matrix / np.maximum(norms, 1e-12)

    def _embed_batch(self, texts: list[str], input_type: str) -> list[list[float]]:
        payload = {
            "model": self.model_name,
            "input": texts,
            "input_type": input_type,
            "truncate": "END",
            "encoding_format": "float",
        }
        req = request.Request(
            f"{self.base_url}/embeddings",
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
                f"NVIDIA embedding {self.model_name} request failed with HTTP {exc.code}: {body}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"NVIDIA embedding {self.model_name} request failed: {exc.reason}"
            ) from exc

        items = sorted(data.get("data", []), key=lambda item: int(item.get("index", 0)))
        vectors = [item.get("embedding") for item in items]
        if len(vectors) != len(texts) or not all(isinstance(vector, list) for vector in vectors):
            raise RuntimeError(f"NVIDIA embedding {self.model_name} returned malformed data: {data}")
        return vectors
