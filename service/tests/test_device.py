from powermind_rag.config import RAGConfig


def test_default_device_is_gpu():
    assert RAGConfig().device == "cuda"
    assert RAGConfig().cuda_arch == "sm_120"


def test_defaults_use_e5_and_gemini_crag_only():
    config = RAGConfig()

    assert config.dense_embedding_model == "E5_Small"
    assert config.relevance_provider == "gemini"
    assert config.chunking_fallback_provider == "none"
