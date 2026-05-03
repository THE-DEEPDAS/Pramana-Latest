from __future__ import annotations

import re
from collections import defaultdict
from time import perf_counter
from pathlib import Path

from powermind_rag.config import RAGConfig
from powermind_rag.device import resolve_device
from powermind_rag.embeddings import DenseEmbedder
from powermind_rag.llm import (
    ChatLLM,
    FallbackChatLLM,
    GeminiChatLLM,
    GroqChatLLM,
    LocalQwen,
    PropositionChunker,
)
from powermind_rag.ocr import MistralTableOCR
from powermind_rag.relevance import RelevanceGrader
from powermind_rag.rrf import reciprocal_rank_fusion
from powermind_rag.schema import Answer, RetrievedChunk, TextChunkRecord
from powermind_rag.text_index import HybridTextIndex, load_text_records, save_text_records
from powermind_rag.verifier import LettuceClaimVerifier
from powermind_rag.visual_index import ColPaliVisualIndex, load_visual_records


NOT_FOUND = "Not found in the document."
FALLBACK_NOT_FOUND = "Fallback: Not found in the document."
TIMING_KEYS = (
    "storage_load",
    "query_expansion",
    "bm25_retrieval",
    "dense_retrieval",
    "keyword_retrieval",
    "text_rrf",
    "visual_retrieval",
    "final_rrf",
    "relevance_grading",
    "generation",
    "verification",
    "total",
)


class MultimodalRAGPipeline:
    def __init__(self, config: RAGConfig | None = None):
        self.config = config or RAGConfig.from_env()
        self.device = resolve_device(self.config.device)
        self.embedder = DenseEmbedder(self.config.dense_embedding_model, device=self.device)
        self.text_index = HybridTextIndex(self.embedder)
        self.visual_index: ColPaliVisualIndex | None = None
        self.text_records: list[TextChunkRecord] = []
        self.generator: ChatLLM | None = None
        self.relevance_grader: RelevanceGrader | None = None
        self.verifier: LettuceClaimVerifier | None = None

    def ingest_pdf(
        self,
        pdf_path: Path,
        doc_type: str = "PDF document",
        section: str = "document content",
        context: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        from powermind_rag.document import document_id_for, extract_pdf_text, render_pdf_pages

        document_id = document_id_for(pdf_path)
        context = context or pdf_path.stem.replace("_", " ")
        base_dir = self.config.storage_dir / document_id
        tables_by_page = defaultdict(str)
        if not self.config.local_only:
            image_paths = render_pdf_pages(pdf_path, base_dir / "pages")
            self._visual_index().build(image_paths, document_id=document_id, metadata=metadata or {})
            ocr = MistralTableOCR(self.config.mistral_api_key, self.config.mistral_ocr_model)
            for table in ocr.extract_markdown_tables(image_paths):
                tables_by_page[table.page_number] += table.markdown + "\n\n"

        use_rule_chunking = self.config.chunking_provider in {"rules", "local-rules"}
        chunker = None if self.config.local_only or use_rule_chunking else PropositionChunker(self._chunking_llm())
        records: list[TextChunkRecord] = []
        chunk_counter = 1
        for page in extract_pdf_text(pdf_path):
            table_markdown = tables_by_page[page.page_number]
            if chunker is None:
                propositions = _local_propositions(_combined_text(page.text, table_markdown))
            else:
                try:
                    propositions = chunker.chunk(
                        page_text=page.text,
                        table_markdown=table_markdown,
                        doc_type=doc_type,
                        section=section,
                        context=context,
                    )
                except Exception as exc:
                    print(
                        f"Proposition LLM failed; using local rule propositions for remaining pages. "
                        f"Reason: {type(exc).__name__}: {exc}",
                        flush=True,
                    )
                    chunker = None
                    propositions = _local_propositions(_combined_text(page.text, table_markdown))
            for proposition in propositions:
                chunk_label = f"c{chunk_counter}"
                chunk_id = f"{document_id}:{chunk_label}"
                prefix = f"This chunk is from {doc_type}, {section}, describing {context}."
                embedding = self.embedder.encode([proposition])[0].tolist()
                records.append(
                    TextChunkRecord(
                        text=proposition,
                        embedding=embedding,
                        chunk_id=chunk_id,
                        document_id=document_id,
                        page_number=page.page_number,
                        modality="text",
                        context_prefix=prefix,
                        metadata={**(metadata or {}), "chunk_label": chunk_label},
                    )
                )
                chunk_counter += 1
        self.text_records.extend(records)
        self.text_index.build(self.text_records)
        save_text_records(records, base_dir / "text_records.json")
        if self.visual_index is not None:
            self.visual_index.save_document_records(document_id, base_dir / "visual_records.json")

    def load_from_storage(self) -> None:
        text_records: list[TextChunkRecord] = []
        visual_records = []
        for text_path in self.config.storage_dir.glob("*/text_records.json"):
            text_records.extend(load_text_records(text_path))
        for visual_path in self.config.storage_dir.glob("*/visual_records.json"):
            visual_records.extend(load_visual_records(visual_path))
        if not text_records and not visual_records:
            raise RuntimeError(f"No ingested records found under {self.config.storage_dir}.")
        self.text_records = text_records
        if text_records:
            self.text_index.build(text_records)
        if visual_records:
            self._visual_index().load_records(visual_records)

    def answer(self, query: str) -> Answer:
        timings = {name: 0.0 for name in TIMING_KEYS}
        total_start = perf_counter()

        def finalize(**kwargs) -> Answer:
            timings["total"] = perf_counter() - total_start
            return Answer(timings=dict(timings), **kwargs)

        if not self.text_records:
            load_start = perf_counter()
            self.load_from_storage()
            timings["storage_load"] = perf_counter() - load_start
        expansion_start = perf_counter()
        expanded_query, keyword_terms = _expand_query(query)
        timings["query_expansion"] = perf_counter() - expansion_start
        text_top_k = max(self.config.text_top_k, 30) if self.config.local_only else self.config.text_top_k
        final_top_k = max(self.config.final_top_k, 20) if self.config.local_only else self.config.final_top_k
        bm25_start = perf_counter()
        bm25_hits = self.text_index.bm25_search(expanded_query, text_top_k)
        timings["bm25_retrieval"] = perf_counter() - bm25_start
        dense_start = perf_counter()
        dense_hits = self.text_index.dense_search(expanded_query, text_top_k)
        timings["dense_retrieval"] = perf_counter() - dense_start
        keyword_start = perf_counter()
        keyword_hits = self.text_index.keyword_search(keyword_terms, text_top_k)
        timings["keyword_retrieval"] = perf_counter() - keyword_start
        text_fusion_start = perf_counter()
        text_hits = reciprocal_rank_fusion([keyword_hits, bm25_hits, dense_hits], k=self.config.rrf_k)
        timings["text_rrf"] = perf_counter() - text_fusion_start
        visual_start = perf_counter()
        if self.config.local_only or self.visual_index is None:
            visual_hits = []
        else:
            visual_hits = self.visual_index.search(query, self.config.visual_top_k)
        timings["visual_retrieval"] = perf_counter() - visual_start
        final_fusion_start = perf_counter()
        candidates = reciprocal_rank_fusion([text_hits, visual_hits], k=self.config.rrf_k)[
            : final_top_k
        ]
        timings["final_rrf"] = perf_counter() - final_fusion_start

        if self.config.local_only:
            graded = [(chunk, 1.0) for chunk in candidates]
        else:
            grade_start = perf_counter()
            graded = self._relevance().grade(query, candidates)
            timings["relevance_grading"] = perf_counter() - grade_start
        supported = [chunk for chunk, score in graded if score >= self.config.relevance_threshold]
        if not supported:
            return finalize(text=NOT_FOUND, retrieved=candidates, is_fallback=False)

        text_evidence = [chunk for chunk in supported if chunk.modality == "text"]
        if not text_evidence:
            return finalize(text=FALLBACK_NOT_FOUND, retrieved=supported, is_fallback=True)

        if self.config.local_only:
            return finalize(
                text=self._extractive_local_answer(
                    query,
                    text_evidence,
                    RuntimeError("POWERMIND_LOCAL_ONLY skips Qwen generation"),
                ),
                retrieved=text_evidence,
                verifier_report={"skipped": "POWERMIND_LOCAL_ONLY disables external verification."},
            )

        try:
            generation_start = perf_counter()
            answer = self._generate_grounded_answer(query, text_evidence)
            timings["generation"] = perf_counter() - generation_start
        except Exception as exc:
            if not self.config.local_only:
                raise
            timings["generation"] = perf_counter() - generation_start
            answer = self._extractive_local_answer(query, text_evidence, exc)
        if answer.strip() == NOT_FOUND:
            return finalize(text=NOT_FOUND, retrieved=text_evidence, is_fallback=False)

        if self.config.local_only:
            return finalize(
                text=answer,
                retrieved=text_evidence,
                verifier_report={"skipped": "POWERMIND_LOCAL_ONLY disables external verification."},
            )

        verification_start = perf_counter()
        verifier_report = self._verifier().verify(answer, [chunk.text for chunk in text_evidence])
        timings["verification"] = perf_counter() - verification_start
        if LettuceClaimVerifier.has_unsupported_content(verifier_report):
            return finalize(
                text=FALLBACK_NOT_FOUND,
                retrieved=text_evidence,
                is_fallback=True,
                verifier_report=verifier_report,
            )
        return finalize(text=answer, retrieved=text_evidence, verifier_report=verifier_report)

    def _generate_grounded_answer(self, query: str, chunks: list[RetrievedChunk]) -> str:
        context_lines = [f"{chunk.citation} {chunk.text}" for chunk in chunks]
        user = f"""
Answer the query using ONLY the retrieved context below.
Every factual statement and every number must have a citation in the exact format [pN:cK].
Do not infer missing numbers. Do not use outside knowledge.
If the context does not explicitly support the answer, return exactly: {NOT_FOUND}

QUERY:
{query}

RETRIEVED CONTEXT:
{chr(10).join(context_lines)}
""".strip()
        return self._generation_llm().generate(
            system="You are a grounded financial/document QA model with zero hallucination tolerance.",
            user=user,
            max_new_tokens=512,
        )

    def _extractive_local_answer(self, query: str, chunks: list[RetrievedChunk], exc: Exception) -> str:
        excerpts = []
        for chunk in chunks[:3]:
            text = " ".join(chunk.text.split())
            if len(text) > 450:
                text = text[:447].rstrip() + "..."
            excerpts.append(f"{text} {chunk.citation}")
        if not excerpts:
            return NOT_FOUND
        return (
            "Local extractive fallback because Qwen generation failed "
            f"({type(exc).__name__}). " + " ".join(excerpts)
        )

    def _visual_index(self) -> ColPaliVisualIndex:
        if self.visual_index is None:
            self.visual_index = ColPaliVisualIndex(self.config.colpali_model_name, device=self.device)
        return self.visual_index

    def _generation_llm(self) -> ChatLLM:
        if self.generator is None:
            if self.config.generation_provider == "groq":
                self.generator = GroqChatLLM(
                    api_key=self.config.groq_api_key,
                    model_name=self.config.groq_generation_model,
                )
            elif self.config.generation_provider in {"local", "qwen"}:
                self.generator = LocalQwen(self.config.qwen_model_path, device=self.device)
            else:
                raise RuntimeError(
                    "Unsupported POWERMIND_GENERATION_PROVIDER. Use 'local' or 'groq'."
                )
        return self.generator

    def _chunking_llm(self) -> ChatLLM:
        if self.config.chunking_provider == "groq":
            primary = GroqChatLLM(
                api_key=self.config.groq_api_key,
                model_name=self.config.groq_chunking_model,
            )
            if self.config.chunking_fallback_provider == "gemini":
                fallback = GeminiChatLLM(
                    api_key=self.config.gemini_api_key_2 or self.config.gemini_api_key,
                    model_name=self.config.gemini_chunking_model,
                )
                return FallbackChatLLM(primary, fallback)
            return primary
        if self.config.chunking_provider == "gemini":
            return GeminiChatLLM(
                api_key=self.config.gemini_api_key_2 or self.config.gemini_api_key,
                model_name=self.config.gemini_chunking_model,
            )
        if self.config.chunking_provider in {"local", "qwen"}:
            return self._generation_llm()
        raise RuntimeError("Unsupported POWERMIND_CHUNKING_PROVIDER. Use 'groq', 'gemini', 'local', or 'rules'.")

    def _relevance(self) -> RelevanceGrader:
        if self.relevance_grader is None:
            if self.config.relevance_provider == "gemini":
                api_key = [
                    key
                    for key in (self.config.gemini_api_key, self.config.gemini_api_key_2)
                    if key
                ]
                model_name = self.config.gemini_relevance_model
            else:
                api_key = self.config.groq_api_key
                model_name = self.config.groq_relevance_model
            self.relevance_grader = RelevanceGrader(
                provider=self.config.relevance_provider,
                api_key=api_key,
                model_name=model_name,
            )
        return self.relevance_grader

    def _verifier(self) -> LettuceClaimVerifier:
        if self.verifier is None:
            self.verifier = LettuceClaimVerifier(
                model_path=self.config.lettuce_model_path,
                device=self.device,
            )
        return self.verifier


def _local_propositions(text: str) -> list[str]:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", clean)
    propositions: list[str] = []
    for part in parts:
        part = part.strip()
        if len(part) < 20:
            continue
        if len(part) <= 700:
            propositions.append(part)
            continue
        words = part.split()
        for start in range(0, len(words), 90):
            chunk = " ".join(words[start : start + 90]).strip()
            if len(chunk) >= 20:
                propositions.append(chunk)
    return propositions


def _combined_text(page_text: str, table_markdown: str) -> str:
    return "\n\n".join(part for part in [page_text, table_markdown] if part.strip())


def _expand_query(query: str) -> tuple[str, list[str]]:
    stopwords = {
        "about",
        "able",
        "after",
        "also",
        "and",
        "are",
        "did",
        "does",
        "for",
        "from",
        "has",
        "have",
        "how",
        "into",
        "its",
        "section",
        "that",
        "the",
        "this",
        "what",
        "when",
        "where",
        "which",
        "who",
        "won",
    }
    quoted_phrases = re.findall(r"['\"]([^'\"]{3,})['\"]", query)
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9&/-]{2,}", query)
    terms = quoted_phrases + [
        token for token in tokens if token.lower() not in stopwords
    ]
    deduped_terms = list(dict.fromkeys(terms))
    return query, deduped_terms
