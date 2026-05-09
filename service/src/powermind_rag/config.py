from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve_path(value: str | None, default: str) -> Path:
    raw = value or default
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


@dataclass(frozen=True)
class RAGConfig:
    storage_dir: Path = Path("storage")
    qwen_model_path: Path = Path("Qwen")
    qwen_vl_model_path: Path = Path("Qwen_VL")
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
    mistral_server_url: str = "https://api.mistral.ai"
    mistral_timeout_ms: int = 120_000
    groq_api_key: str | None = None
    gemini_api_key: str | None = None
    gemini_api_key_2: str | None = None
    relevance_provider: str = "gemini"
    groq_relevance_model: str = "llama-3.1-8b-instant"
    gemini_relevance_model: str = "gemini-2.5-flash"
    generation_provider: str = "local"
    image_generation_provider: str = "nvidia"
    groq_generation_model: str = "llama-3.3-70b-versatile"
    openrouter_api_key: str | None = None
    openrouter_generation_model: str = "liquid/lfm-2.5-1.2b-instruct:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_http_referer: str = "http://localhost/powermind"
    openrouter_app_title: str = "PowerMind RAG"
    enable_visual_understanding: bool = False
    refresh_visual_understanding: bool = False
    visual_understanding_provider: str = "nvidia"
    nvidia_api_key: str | None = None
    nvidia_vlm_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_vlm_model: str = "nvidia/nemotron-nano-12b-v2-vl"
    nvidia_generation_model: str = "nvidia/nemotron-nano-12b-v2-vl"
    nvidia_vlm_max_tokens: int = 4096
    nvidia_vlm_image_max_bytes: int = 100_000
    nvidia_vlm_image_max_side: int = 1400
    nvidia_vlm_timeout_seconds: int = 600
    qwen_vl_device: str | None = None
    qwen_vl_visual_max_tokens: int = 384
    enable_query_visual_retrieval: bool = False
    enable_query_vlm_fallback: bool = True
    include_page_images_in_answers: bool = False
    load_imported_records: bool = False
    enable_verification: bool = False
    chunking_provider: str = "rules"
    groq_chunking_model: str = "llama-3.3-70b-versatile"
    chunking_fallback_provider: str = "none"
    gemini_chunking_model: str = "gemini-2.5-flash"
    lettuce_model_path: str = "KRLabsOrg/lettucedect-base-modernbert-en-v1"
    local_only: bool = False

    @classmethod
    def from_env(cls) -> "RAGConfig":
        load_dotenv()
        local_only = os.getenv("POWERMIND_LOCAL_ONLY", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        generation_provider = os.getenv("POWERMIND_GENERATION_PROVIDER", "local").strip().lower()
        image_generation_provider = os.getenv(
            "POWERMIND_IMAGE_PROVIDER",
            generation_provider,
        ).strip().lower()
        return cls(
            storage_dir=_resolve_path(os.getenv("POWERMIND_STORAGE_DIR"), "storage"),
            qwen_model_path=_resolve_path(os.getenv("QWEN_MODEL_PATH"), "Qwen"),
            qwen_vl_model_path=_resolve_path(os.getenv("QWEN_VL_MODEL_PATH"), "Qwen_VL"),
            dense_embedding_model=os.getenv("POWERMIND_DENSE_MODEL", "E5_Small"),
            colpali_model_name=os.getenv("POWERMIND_COLPALI_MODEL", "vidore/colpali-v1.2"),
            device=os.getenv("POWERMIND_DEVICE", "cuda"),
            cuda_arch=os.getenv("POWERMIND_CUDA_ARCH", "sm_120"),
            mistral_api_key=os.getenv("MISTRAL_API_KEY"),
            mistral_ocr_model=os.getenv("MISTRAL_OCR_MODEL", "mistral-ocr-latest"),
            mistral_server_url=os.getenv("MISTRAL_SERVER_URL", "https://api.mistral.ai").rstrip("/"),
            mistral_timeout_ms=int(os.getenv("MISTRAL_TIMEOUT_MS", "120000")),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            gemini_api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"),
            gemini_api_key_2=os.getenv("GEMINI_API_KEY_2"),
            relevance_provider=os.getenv("POWERMIND_RELEVANCE_PROVIDER", "gemini").strip().lower(),
            groq_relevance_model=os.getenv("GROQ_RELEVANCE_MODEL", "llama-3.1-8b-instant"),
            gemini_relevance_model=os.getenv("GEMINI_RELEVANCE_MODEL", "gemini-2.5-flash"),
            generation_provider=generation_provider,
            image_generation_provider=image_generation_provider,
            groq_generation_model=os.getenv("GROQ_GENERATION_MODEL", "llama-3.3-70b-versatile"),
            openrouter_api_key=os.getenv("OPEN_ROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY"),
            openrouter_generation_model=os.getenv(
                "OPEN_ROUTER_GENERATION_MODEL",
                os.getenv(
                    "OPENROUTER_GENERATION_MODEL",
                    "liquid/lfm-2.5-1.2b-instruct:free",
                ),
            ),
            openrouter_base_url=os.getenv(
                "OPEN_ROUTER_BASE_URL",
                os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            ).rstrip("/"),
            openrouter_http_referer=os.getenv(
                "OPEN_ROUTER_HTTP_REFERER",
                os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost/powermind"),
            ),
            openrouter_app_title=os.getenv(
                "OPEN_ROUTER_APP_TITLE",
                os.getenv("OPENROUTER_APP_TITLE", "PowerMind RAG"),
            ),
            enable_visual_understanding=os.getenv(
                "POWERMIND_ENABLE_VISUAL_UNDERSTANDING", ""
            ).strip().lower()
            in {"1", "true", "yes", "on"},
            refresh_visual_understanding=os.getenv(
                "POWERMIND_REFRESH_VISUAL_UNDERSTANDING", ""
            ).strip().lower()
            in {"1", "true", "yes", "on"},
            visual_understanding_provider=os.getenv(
                "POWERMIND_VISUAL_UNDERSTANDING_PROVIDER", "nvidia"
            ).strip().lower(),
            nvidia_api_key=(
                os.getenv("NVIDIA_KEY")
                or os.getenv("NVIDIA_API_KEY")
                or os.getenv("NVIDIA_NIM_API_KEY")
            ),
            nvidia_vlm_base_url=os.getenv(
                "NVIDIA_VLM_BASE_URL",
                "https://integrate.api.nvidia.com/v1",
            ).rstrip("/"),
            nvidia_vlm_model=os.getenv(
                "NVIDIA_VLM_MODEL",
                "nvidia/nemotron-nano-12b-v2-vl",
            ),
            nvidia_generation_model=os.getenv(
                "NVIDIA_GENERATION_MODEL",
                os.getenv("NVIDIA_VLM_MODEL", "nvidia/nemotron-nano-12b-v2-vl"),
            ),
            nvidia_vlm_max_tokens=int(os.getenv("NVIDIA_VLM_MAX_TOKENS", "4096")),
            nvidia_vlm_image_max_bytes=int(os.getenv("NVIDIA_VLM_IMAGE_MAX_BYTES", "100000")),
            nvidia_vlm_image_max_side=int(os.getenv("NVIDIA_VLM_IMAGE_MAX_SIDE", "1400")),
            nvidia_vlm_timeout_seconds=int(os.getenv("NVIDIA_VLM_TIMEOUT_SECONDS", "600")),
            qwen_vl_device=(os.getenv("QWEN_VL_DEVICE") or "").strip().lower() or None,
            qwen_vl_visual_max_tokens=int(os.getenv("QWEN_VL_VISUAL_MAX_TOKENS", "384")),
            enable_query_visual_retrieval=os.getenv(
                "POWERMIND_ENABLE_QUERY_VISUAL_RETRIEVAL", ""
            ).strip().lower()
            in {"1", "true", "yes", "on"},
            enable_query_vlm_fallback=os.getenv(
                "POWERMIND_ENABLE_QUERY_VLM_FALLBACK", "1"
            ).strip().lower()
            in {"1", "true", "yes", "on"},
            include_page_images_in_answers=os.getenv(
                "POWERMIND_INCLUDE_PAGE_IMAGES_IN_ANSWERS", ""
            ).strip().lower()
            in {"1", "true", "yes", "on"},
            load_imported_records=os.getenv(
                "POWERMIND_LOAD_IMPORTED_RECORDS", ""
            ).strip().lower()
            in {"1", "true", "yes", "on"},
            chunking_provider=os.getenv("POWERMIND_CHUNKING_PROVIDER", "rules").strip().lower(),
            groq_chunking_model=os.getenv("GROQ_CHUNKING_MODEL", "llama-3.3-70b-versatile"),
            chunking_fallback_provider=os.getenv(
                "POWERMIND_CHUNKING_FALLBACK_PROVIDER", "none"
            ).strip().lower(),
            gemini_chunking_model=os.getenv("GEMINI_CHUNKING_MODEL", "gemini-2.5-flash"),
            lettuce_model_path=os.getenv(
                "LETTUCE_MODEL_PATH",
                "KRLabsOrg/lettucedect-base-modernbert-en-v1",
            ),
            enable_verification=os.getenv("POWERMIND_ENABLE_VERIFICATION", "").strip().lower()
            in {"1", "true", "yes", "on"},
            local_only=local_only,
        )
