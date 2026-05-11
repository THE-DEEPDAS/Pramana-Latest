from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

# FastMCP deploy/inspect may execute this file directly from the repo root
# without installing the package. Make service/src importable in that case.
SERVICE_SRC = Path(__file__).resolve().parents[1]
if str(SERVICE_SRC) not in sys.path:
    sys.path.insert(0, str(SERVICE_SRC))

from powermind_rag.config import RAGConfig
from powermind_rag.pipeline import MultimodalRAGPipeline
from powermind_rag.schema import RetrievedChunk


mcp = FastMCP(
    name="Pramana RAG",
    instructions=(
        "Pramana exposes document ingestion and retrieval tools. For final answers, "
        "call retrieve_evidence and synthesize only from returned evidence and citations. "
        "The server does not need to be the final inference LLM. If credentials are "
        "missing, call environment_status and configure_environment before retrieval "
        "or ingestion."
    ),
)

_pipeline: MultimodalRAGPipeline | None = None

_ALLOWED_ENV_KEYS = {
    "NVIDIA_KEY",
    "NVIDIA_API_KEY",
    "NVIDIA_NIM_API_KEY",
    "NVIDIA_EMBEDDING_MODEL",
    "NVIDIA_VLM_MODEL",
    "NVIDIA_GENERATION_MODEL",
    "NVIDIA_VLM_BASE_URL",
    "MISTRAL_API_KEY",
    "MISTRAL_SERVER_URL",
    "GEMINI_API_KEY",
    "GEMINI_API_KEY_1",
    "GEMINI_API_KEY_2",
    "GEMINI_API_KEY_3",
    "GEMINI_API_KEY_4",
    "GEMINI_API_KEY_5",
    "GEMINI_API_KEY_6",
    "GEMINI_1",
    "GEMINI_2",
    "GEMINI_3",
    "GEMINI_4",
    "GEMINI_5",
    "GEMINI_6",
    "GEMINI_RELEVANCE_MODEL",
    "POWERMIND_STORAGE_DIR",
    "POWERMIND_DEVICE",
    "POWERMIND_ENABLE_VISUAL_UNDERSTANDING",
    "POWERMIND_VISUAL_UNDERSTANDING_PROVIDER",
    "POWERMIND_RELEVANCE_PROVIDER",
    "POWERMIND_ALLOW_LEXICAL_CRAG_FALLBACK",
    "POWERMIND_ENABLE_QUERY_VISUAL_RETRIEVAL",
    "POWERMIND_ENABLE_COLPALI_VISUAL_INDEX",
    "POWERMIND_CHUNKING_PROVIDER",
}


def _get_pipeline() -> MultimodalRAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = MultimodalRAGPipeline(RAGConfig.from_env())
    return _pipeline


def _reset_pipeline() -> None:
    global _pipeline
    _pipeline = None


def _has_any_env(*names: str) -> bool:
    return any((os.getenv(name) or "").strip().strip('"') for name in names)


def _gemini_configured() -> bool:
    return _has_any_env(
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY_1",
        "GEMINI_API_KEY_2",
        "GEMINI_API_KEY_3",
        "GEMINI_API_KEY_4",
        "GEMINI_API_KEY_5",
        "GEMINI_API_KEY_6",
        "GEMINI_1",
        "GEMINI_2",
        "GEMINI_3",
        "GEMINI_4",
        "GEMINI_5",
        "GEMINI_6",
    )


def _missing_for_retrieval(use_relevance: bool) -> list[str]:
    missing = []
    if not _has_any_env("NVIDIA_KEY", "NVIDIA_API_KEY", "NVIDIA_NIM_API_KEY"):
        missing.append("NVIDIA_KEY")
    relevance_provider = os.getenv("POWERMIND_RELEVANCE_PROVIDER", "gemini").strip().lower()
    if use_relevance and relevance_provider == "gemini" and not _gemini_configured():
        missing.append("GEMINI_API_KEY_1")
    return missing


def _missing_for_ingest() -> list[str]:
    missing = _missing_for_retrieval(use_relevance=False)
    visual_enabled = os.getenv("POWERMIND_ENABLE_VISUAL_UNDERSTANDING", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    visual_provider = os.getenv("POWERMIND_VISUAL_UNDERSTANDING_PROVIDER", "gemini_nvidia").strip().lower()
    if visual_enabled and "gemini" in visual_provider and not _gemini_configured():
        missing.append("GEMINI_API_KEY_1")
    if (
        visual_enabled
        and "nvidia" in visual_provider
        and not _has_any_env("NVIDIA_KEY", "NVIDIA_API_KEY", "NVIDIA_NIM_API_KEY")
        and "NVIDIA_KEY" not in missing
    ):
        missing.append("NVIDIA_KEY")
    if os.getenv("POWERMIND_CHUNKING_PROVIDER", "rules").strip().lower() == "gemini" and not _gemini_configured():
        missing.append("GEMINI_API_KEY_1")
    return list(dict.fromkeys(missing))


def _configuration_response(operation: str, missing: list[str]) -> dict[str, Any]:
    return {
        "status": "needs_configuration",
        "operation": operation,
        "missing_env_vars": missing,
        "message": (
            "Ask the user for only these missing values, then call configure_environment "
            "with an env mapping. The final inference LLM remains the MCP host."
        ),
        "example_tool_call": {
            "env": {name: "<secret>" for name in missing},
        },
    }


def _chunk_payload(chunk: RetrievedChunk) -> dict[str, Any]:
    return {
        "id": chunk.id,
        "citation": chunk.citation,
        "text": chunk.text,
        "document_id": chunk.document_id,
        "page_number": chunk.page_number,
        "modality": chunk.modality,
        "rank": chunk.rank,
        "score": chunk.score,
        "metadata": chunk.metadata,
    }


@mcp.tool
def environment_status() -> dict[str, Any]:
    """Show which credentials/settings are currently configured without revealing values."""
    config = RAGConfig.from_env()
    retrieval_missing = _missing_for_retrieval(use_relevance=True)
    ingest_missing = _missing_for_ingest()
    configured = [
        key
        for key in sorted(_ALLOWED_ENV_KEYS)
        if key in os.environ and (os.getenv(key) or "").strip()
    ]
    return {
        "storage_dir": str(config.storage_dir),
        "configured_env_vars": configured,
        "retrieval_ready": not retrieval_missing,
        "ingest_ready": not ingest_missing,
        "missing_for_retrieval": retrieval_missing,
        "missing_for_ingest": ingest_missing,
        "note": (
            "Values are intentionally not returned. If anything is missing, ask the user "
            "for only those variables and pass them to configure_environment."
        ),
    }


@mcp.tool
def configure_environment(env: dict[str, str]) -> dict[str, Any]:
    """Set allowed Pramana environment variables for this running MCP server process."""
    accepted = []
    rejected = []
    for key, value in env.items():
        normalized_key = key.strip()
        if normalized_key not in _ALLOWED_ENV_KEYS:
            rejected.append(normalized_key)
            continue
        os.environ[normalized_key] = str(value).strip().strip('"')
        accepted.append(normalized_key)
    if accepted:
        _reset_pipeline()
    status = environment_status()
    return {
        "status": "configured" if accepted else "no_changes",
        "accepted_env_vars": sorted(accepted),
        "rejected_env_vars": sorted(rejected),
        "environment_status": status,
    }


@mcp.tool
def retrieve_evidence(query: str, top_k: int = 8, use_relevance: bool = False) -> dict[str, Any]:
    """Retrieve cited document evidence for the host LLM to answer from.

    Use this tool when the caller wants its own model to perform the final
    inference. The returned chunks are evidence, not a final answer.
    """
    missing = _missing_for_retrieval(use_relevance=use_relevance)
    if missing:
        return _configuration_response("retrieve_evidence", missing)
    safe_top_k = max(1, min(top_k, 30))
    pipeline = _get_pipeline()
    chunks, timings = pipeline.retrieve_evidence(
        query=query,
        top_k=safe_top_k,
        use_relevance=use_relevance,
    )
    return {
        "query": query,
        "answering_contract": (
            "The host LLM must answer using only the evidence array. Cite every "
            "factual claim with the provided citation. If the evidence does not "
            "support the answer, say: Not found in the document."
        ),
        "evidence": [_chunk_payload(chunk) for chunk in chunks],
        "timings": timings,
    }


@mcp.tool
def ingest_pdf(
    pdf_path: str,
    doc_type: str = "PDF document",
    section: str = "document content",
    context: str | None = None,
) -> dict[str, Any]:
    """Ingest a PDF into Pramana storage so it can be retrieved later."""
    missing = _missing_for_ingest()
    if missing:
        return _configuration_response("ingest_pdf", missing)
    path = Path(pdf_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    report = _get_pipeline().ingest_pdf(path, doc_type=doc_type, section=section, context=context)
    return dict(report)


@mcp.tool
def list_documents() -> dict[str, Any]:
    """List ingested documents available in Pramana storage."""
    config = RAGConfig.from_env()
    documents = []
    for text_path in sorted(config.storage_dir.glob("*/text_records.json")):
        document_dir = text_path.parent
        documents.append(
            {
                "document_id": document_dir.name,
                "text_records_path": str(text_path),
                "has_page_images": (document_dir / "pages").exists(),
                "has_visual_analysis": (document_dir / "visual_page_analysis.json").exists(),
            }
        )
    return {"storage_dir": str(config.storage_dir), "documents": documents}


@mcp.prompt
def answer_from_pramana_evidence(question: str) -> str:
    """Host-side prompt for answering from retrieved Pramana evidence."""
    return f"""
Use the Pramana retrieve_evidence tool for this question:

{question}

After retrieving evidence, answer using only the returned evidence array.
Cite every factual claim with the exact citation field from the evidence.
If the evidence does not explicitly support the answer, say exactly:
Not found in the document.
""".strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Pramana MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "streamable-http"],
        default="http",
        help="Use stdio for local MCP clients or http/streamable-http for remote clients.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind for HTTP transport.")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind for HTTP transport.")
    args = parser.parse_args()
    transport = "http" if args.transport == "streamable-http" else args.transport
    if transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport=transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
