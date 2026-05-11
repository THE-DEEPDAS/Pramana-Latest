from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from powermind_rag.config import RAGConfig
from powermind_rag.pipeline import MultimodalRAGPipeline
from powermind_rag.schema import RetrievedChunk


mcp = FastMCP(
    name="Pramana RAG",
    instructions=(
        "Pramana exposes document ingestion and retrieval tools. For final answers, "
        "call retrieve_evidence and synthesize only from returned evidence and citations. "
        "The server does not need to be the final inference LLM."
    ),
)

_pipeline: MultimodalRAGPipeline | None = None


def _get_pipeline() -> MultimodalRAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = MultimodalRAGPipeline(RAGConfig.from_env())
    return _pipeline


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
def retrieve_evidence(query: str, top_k: int = 8, use_relevance: bool = True) -> dict[str, Any]:
    """Retrieve cited document evidence for the host LLM to answer from.

    Use this tool when the caller wants its own model to perform the final
    inference. The returned chunks are evidence, not a final answer.
    """
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
