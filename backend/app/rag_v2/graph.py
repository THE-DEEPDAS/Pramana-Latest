"""
LangGraph Orchestration for RAG v2 — simplified 3-node graph.

retrieve → generate (chunks found)
         → fallback  (no chunks)

History is passed directly to the generate node — no query rewriting,
no per-chunk LLM grading calls.
"""
from __future__ import annotations

import logging
import re
from typing import Any, TypedDict

from app.rag_v2.config import RagV2Config
from app.rag_v2.crag import NOT_FOUND, page_level_fallback, verify_answer
from app.rag_v2.embedder import build_embedder
from app.rag_v2.llm import build_llm
from app.rag_v2.vector_store import PineconeStore

logger = logging.getLogger(__name__)
CONTEXT_TEXT_LIMIT = 1400
PAGE_EXPANSION_LIMIT = 4
PAGE_EXPANSION_TOP_K = 20
MAX_CONTEXT_CHUNKS = 28


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class RagState(TypedDict, total=False):
    query: str
    history: list[dict[str, str]]        # prior {role, content} turns
    chunks: list[dict[str, Any]]         # Pinecone top-k matches
    answer: str
    sources: list[dict[str, Any]]
    crag_report: dict[str, Any]
    is_fallback: bool


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def _make_retrieve(embedder, store: PineconeStore, top_k: int):
    def retrieve(state: RagState) -> RagState:
        if hasattr(embedder, "embed_query"):
            vec = embedder.embed_query(state["query"]).tolist()
        else:
            vec = embedder.embed([state["query"]])[0].tolist()
        chunks = store.query(vector=vec, top_k=top_k)
        explicit_pages = _explicit_page_numbers(state["query"])
        chunks = _expand_explicit_pages(
            store=store,
            vector=vec,
            page_numbers=explicit_pages,
            chunks=chunks,
        )
        chunks = _expand_page_context(store=store, vector=vec, chunks=chunks)
        if explicit_pages:
            chunks = _prioritize_explicit_pages(chunks, explicit_pages)
        logger.debug("Retrieved %d chunks for query: %s", len(chunks), state["query"])
        return {**state, "chunks": chunks}
    return retrieve


def _explicit_page_numbers(query: str) -> list[int]:
    return sorted({int(match) for match in re.findall(r"\bpage\s+(\d+)\b", query, flags=re.I)})


def _expand_explicit_pages(
    *,
    store: PineconeStore,
    vector: list[float],
    page_numbers: list[int],
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not page_numbers:
        return chunks

    merged: dict[str, dict[str, Any]] = {chunk["id"]: chunk for chunk in chunks}
    for page_number in page_numbers[:2]:
        page_chunks = store.query(
            vector=vector,
            top_k=PAGE_EXPANSION_TOP_K,
            filter={
                "page_number": {"$eq": page_number},
            },
        )
        for chunk in page_chunks:
            if int(chunk.get("metadata", {}).get("index_level", 0) or 0) != 0:
                continue
            merged.setdefault(chunk["id"], chunk)
    return list(merged.values())


def _prioritize_explicit_pages(
    chunks: list[dict[str, Any]],
    explicit_pages: list[int],
) -> list[dict[str, Any]]:
    explicit = set(explicit_pages)
    return sorted(
        chunks,
        key=lambda item: (
            0 if item.get("metadata", {}).get("page_number") in explicit else 1,
            0 if item.get("metadata", {}).get("embedding_channel") == "vlm" else 1,
            int(item.get("metadata", {}).get("chunk_index", 9999) or 9999),
            -float(item.get("score", 0)),
        ),
    )[:MAX_CONTEXT_CHUNKS]


def _expand_page_context(
    *,
    store: PineconeStore,
    vector: list[float],
    chunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Pull a few more chunks from the same pages as the best matches.

    PDF answers often span a visual page split into multiple text/VLM chunks.
    Pure top-k can retrieve only the legend/footer half of a page, so this adds
    same-page context while preserving the original semantic matches first.
    """
    merged: dict[str, dict[str, Any]] = {chunk["id"]: chunk for chunk in chunks}
    pages: list[tuple[str, int]] = []
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        if int(meta.get("index_level", 0) or 0) != 0:
            continue
        document_id = str(meta.get("document_id") or "")
        page_number = meta.get("page_number")
        if not document_id or not isinstance(page_number, int):
            continue
        page_key = (document_id, page_number)
        if page_key not in pages:
            pages.append(page_key)
        if len(pages) >= PAGE_EXPANSION_LIMIT:
            break

    for document_id, page_number in pages:
        page_chunks = store.query(
            vector=vector,
            top_k=PAGE_EXPANSION_TOP_K,
            filter={
                "document_id": {"$eq": document_id},
                "page_number": {"$eq": page_number},
            },
        )
        for chunk in page_chunks:
            if int(chunk.get("metadata", {}).get("index_level", 0) or 0) != 0:
                continue
            merged.setdefault(chunk["id"], chunk)

    page_rank = {page_key: index for index, page_key in enumerate(pages)}
    return sorted(
        merged.values(),
        key=lambda item: (
            page_rank.get(
                (
                    str(item.get("metadata", {}).get("document_id") or ""),
                    item.get("metadata", {}).get("page_number"),
                ),
                999,
            ),
            int(item.get("metadata", {}).get("page_number", 9999) or 9999),
            0 if item.get("metadata", {}).get("embedding_channel") == "vlm" else 1,
            int(item.get("metadata", {}).get("chunk_index", 9999) or 9999),
            -float(item.get("score", 0)),
        ),
    )[:MAX_CONTEXT_CHUNKS]


def _make_generate(llm, config: RagV2Config):
    def generate(state: RagState) -> RagState:
        query = state["query"]
        chunks = _rank_generation_chunks(query, state.get("chunks", []))
        history = state.get("history", [])

        context_parts, sources = [], []
        for chunk in chunks:
            meta = chunk["metadata"]
            text = str(meta.get("text", ""))
            if len(text) > CONTEXT_TEXT_LIMIT:
                text = text[:CONTEXT_TEXT_LIMIT].rsplit(" ", 1)[0] + " ..."
            level = int(meta.get("index_level", 0) or 0)
            page = meta.get("page_number", "?")
            chunk_idx = meta.get("chunk_index", "?")
            if level > 0:
                batch_idx = meta.get("summary_batch_index", "?")
                citation = f"[l{level}:n{batch_idx}]"
            else:
                citation = f"[p{page}:c{chunk_idx}]"
            context_parts.append(
                f"{citation}\n"
                f"file: {meta.get('filename', '')}\n"
                f"page: {page}\n"
                f"level: {level}\n"
                f"channel: {meta.get('embedding_channel', '')}\n"
                "passage:\n"
                f"{text}"
            )
            sources.append({
                "chunk_id": chunk["id"],
                "document_id": meta.get("document_id", ""),
                "filename": meta.get("filename", ""),
                "index_level": level,
                "embedding_channel": meta.get("embedding_channel", ""),
                "page_number": page,
                "chunk_index": chunk_idx,
                "score": chunk["score"],
                "citation": citation,
                "text": meta.get("text", ""),
            })

        system = """\
You are PowerMind, a grounded document QA assistant.

Use ONLY the provided context passages. Do not use memory or outside knowledge.

Anti-hallucination rules:
- If the answer is not explicitly supported by the context, output exactly: Not found in the Documents
- Treat extracted visual descriptions, image captions, OCR text, and table text in the context as document evidence.
- For visual questions, answer from what the context says is visible. It is OK to say "the visual shows" when the context describes an image.
- If a visual question asks what product/type/object appears in an image, use the exact visible object or product words from the visual description. Do not require the context to repeat the user's wording.
- A direct visual interpretation is allowed when it simply restates visible objects from the context, for example answering "solar panels" when the context says an image shows a manufacturing facility with solar panels.
- When the question says "based on the visual", "appears", or asks what can be seen, answer with the visible object/product from the context; use "appears to be" only for this visual-identification case.
- For visual-identification questions, a passage saying "Image of ... with X" is explicit evidence for answering X.
- Do not require an exact keyword match between the question and context; use semantically matching evidence when the entity, table, slide, or visual description is clearly relevant.
- Every factual claim, number, date, percentage, currency amount, CAGR, ratio, table value, and entity name must be copied from the context and cited.
- Cite each supported fact with its source tag exactly as shown, for example [p2:c5].
- Do not calculate or infer unless the context provides the formula and all inputs. If you calculate, show the source values and the arithmetic.
- If passages conflict, report the conflict with citations instead of choosing one silently.
- Do not soften missing evidence with phrases like "likely" or "may"; use the exact not-found response.

Answer format:
- Give the direct answer first.
- Include only the evidence needed to answer the query.
- Keep citations next to the claims they support.
- Answer in one complete sentence unless the question asks for multiple items.
- For table questions, read the row and column labels carefully and return the exact cell value(s).
- For waterfall charts with categories like Established and Incubating, use the category value, not the consolidated total.
- For stacked/segmented charts, map component values to legend/category order. If the legend says "Established Businesses" then "Incubating Businesses", the first component value is Established and the second component value is Incubating.
- For infographic/portfolio questions, preserve hierarchy exactly as written in the context: parent column/category, company/entity, and percentage.
- Do not stop mid-sentence. If the answer contains a number, include the full number, unit, and citation.
- Keep the answer under 80 words.
"""

        # Build messages: history + context + current question
        messages = list(history)
        messages.append({
            "role": "user",
            "content": (
                f"Context:\n{chr(10).join(context_parts)}\n\n"
                f"Question: {query}\n\n"
                "Return a complete, concise answer with citations. Do not end mid-sentence."
            ),
        })

        answer = llm.chat(messages, system=system, max_tokens=1024)
        if _looks_incomplete(answer):
            repair_messages = [
                *messages,
                {
                    "role": "assistant",
                    "content": answer,
                },
                {
                    "role": "user",
                    "content": (
                        "Your previous answer appears incomplete. Return the same answer as "
                        "one complete sentence with all citations closed. Use only the context."
                    ),
                },
            ]
            answer = llm.chat(repair_messages, system=system, max_tokens=256)
        crag_report = verify_answer(
            config=config,
            query=query,
            answer=answer,
            chunks=chunks,
        )
        if crag_report.get("needs_page_fallback"):
            page_report = page_level_fallback(config=config, query=query, chunks=chunks)
            crag_report = {**crag_report, "page_fallback": page_report}
            answer = _apply_page_fallback_answer(answer, page_report)

        return {
            **state,
            "answer": answer,
            "sources": sources,
            "crag_report": crag_report,
            "is_fallback": answer == NOT_FOUND,
        }
    return generate


def _looks_incomplete(answer: str) -> bool:
    stripped = answer.strip()
    if not stripped:
        return False
    if stripped.count("[") != stripped.count("]"):
        return True
    if stripped.endswith((",", "and", "with", "shown", "exact", "percentage", "c")):
        return True
    return False


def _rank_generation_chunks(query: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    q = query.lower()
    visual_query = any(token in q for token in ["visual", "image", "appears", "shows", "seen"])
    if not visual_query:
        return chunks

    important_terms = [
        term
        for term in re.findall(r"[a-zA-Z0-9]+", q)
        if len(term) > 3 and term not in {"what", "type", "based", "there", "from", "with", "that", "this"}
    ]

    def score(chunk: dict[str, Any]) -> tuple[int, int, float]:
        meta = chunk.get("metadata", {})
        text = str(meta.get("text", "")).lower()
        term_hits = sum(1 for term in important_terms if term in text)
        visual_hits = sum(
            1
            for term in ["image", "visual", "manufacturing", "facility", "product", "appears"]
            if term in text
        )
        channel_bonus = 1 if meta.get("embedding_channel") == "vlm" else 0
        return (term_hits + visual_hits + channel_bonus, channel_bonus, float(chunk.get("score", 0)))

    ranked = sorted(chunks, key=score, reverse=True)
    return ranked[:10]



def _fallback(state: RagState) -> RagState:
    return {
        **state,
        "answer": NOT_FOUND,
        "sources": [],
        "crag_report": {"status": "no_chunks", "needs_page_fallback": False},
        "is_fallback": True,
    }


def _route(state: RagState) -> str:
    return "generate" if state.get("chunks") else "fallback"


def _apply_page_fallback_answer(answer: str, page_report: dict[str, Any]) -> str:
    if page_report.get("found") and page_report.get("answer"):
        return str(page_report["answer"])
    return answer





# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph(config: RagV2Config):
    try:
        from langgraph.graph import StateGraph, END
    except ImportError as exc:
        raise ImportError("Run: pip install langgraph") from exc

    embedder = build_embedder(config)
    store = PineconeStore(config)
    llm = build_llm(config)

    builder = StateGraph(RagState)
    builder.add_node("retrieve", _make_retrieve(embedder, store, config.top_k))
    builder.add_node("generate", _make_generate(llm, config))
    builder.add_node("fallback", _fallback)

    builder.set_entry_point("retrieve")
    builder.add_conditional_edges("retrieve", _route, {"generate": "generate", "fallback": "fallback"})
    builder.add_edge("generate", END)
    builder.add_edge("fallback", END)

    return builder.compile()
