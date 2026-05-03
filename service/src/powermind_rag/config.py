from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

@dataclass(frozen=True)
class RAGConfig:
    storage_dir: Path = Path("storage")
    qwen_model_path: Path = Path("Qwen")
    dense_embedding_model: str = "E5_Small"
    colpali_model_name: str = "vidore/colpali-v1.2"
    device: str = "cuda"
    cuda_arch: str = "sm_120"
    visual_top_k: int = 5
    text_top_k: int = 12
    final_top_k: int = 16
    relevance_threshold: float = 0.4
    rrf_k: int = 60
    mistral_api_key: str | None = None
    mistral_ocr_model: str = "mistral-ocr-latest"
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    gemini_api_key_2: str | None = None
    relevance_provider: str = "gemini"
    groq_relevance_model: str = "llama-3.1-8b-instant"
    gemini_relevance_model: str = "gemini-2.5-flash"
    generation_provider: str = "local"
    groq_generation_model: str = "llama-3.3-70b-versatile"
    chunking_provider: str = "groq"
    groq_chunking_model: str = "llama-3.3-70b-versatile"
    chunking_fallback_provider: str = "none"
    gemini_chunking_model: str = "gemini-2.5-flash"
    lettuce_model_path: str = "KRLabsOrg/lettucedect-base-modernbert-en-v1"
    local_only: bool = False

    @classmethod
    def from_env(cls) -> "RAGConfig":
        load_dotenv()
        local_only = os.getenv("POWERMIND_LOCAL_ONLY", "").strip().lower() in {"1", "true", "yes", "on"}
        return cls(
            storage_dir=Path(os.getenv("POWERMIND_STORAGE_DIR", "storage")),
            qwen_model_path=Path(os.getenv("QWEN_MODEL_PATH", "Qwen")),
            dense_embedding_model=os.getenv(
                "POWERMIND_DENSE_MODEL", "E5_Small"
            ),
            colpali_model_name=os.getenv("POWERMIND_COLPALI_MODEL", "vidore/colpali-v1.2"),
            device=os.getenv("POWERMIND_DEVICE", "cuda"),
            cuda_arch=os.getenv("POWERMIND_CUDA_ARCH", "sm_120"),
            mistral_api_key=os.getenv("MISTRAL_API_KEY"),
            mistral_ocr_model=os.getenv("MISTRAL_OCR_MODEL", "mistral-ocr-latest"),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            gemini_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
            gemini_api_key_2=os.getenv("GEMINI_API_KEY_2"),
            relevance_provider=os.getenv("POWERMIND_RELEVANCE_PROVIDER", "gemini").strip().lower(),
            groq_relevance_model=os.getenv("GROQ_RELEVANCE_MODEL", "llama-3.1-8b-instant"),
            gemini_relevance_model=os.getenv("GEMINI_RELEVANCE_MODEL", "gemini-2.5-flash"),
            generation_provider=os.getenv("POWERMIND_GENERATION_PROVIDER", "local").strip().lower(),
            groq_generation_model=os.getenv("GROQ_GENERATION_MODEL", "llama-3.3-70b-versatile"),
            chunking_provider=os.getenv("POWERMIND_CHUNKING_PROVIDER", "groq").strip().lower(),
            groq_chunking_model=os.getenv("GROQ_CHUNKING_MODEL", "llama-3.3-70b-versatile"),
            chunking_fallback_provider=os.getenv(
                "POWERMIND_CHUNKING_FALLBACK_PROVIDER", "none"
            ).strip().lower(),
            gemini_chunking_model=os.getenv("GEMINI_CHUNKING_MODEL", "gemini-2.5-flash"),
            lettuce_model_path=os.getenv(
                "LETTUCE_MODEL_PATH",
                "KRLabsOrg/lettucedect-base-modernbert-en-v1",
            ),
            local_only=local_only,
        )
