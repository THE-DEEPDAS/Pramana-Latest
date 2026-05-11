from __future__ import annotations

import re
import json
from collections import defaultdict
from dataclasses import replace
from time import perf_counter
from pathlib import Path
from typing import Any

from powermind_rag.config import RAGConfig
from powermind_rag.device import resolve_device
from powermind_rag.embeddings import DenseEmbedder
from powermind_rag.llm import (
    ChatLLM,
    FallbackChatLLM,
    GeminiChatLLM,
    GroqChatLLM,
    NvidiaChatLLM,
    OpenRouterChatLLM,
    PropositionChunker,
)
from powermind_rag.ocr import MistralTableOCR
from powermind_rag.relevance import RelevanceGrader
from powermind_rag.rrf import reciprocal_rank_fusion
from powermind_rag.schema import Answer, RetrievedChunk, TextChunkRecord
from powermind_rag.text_index import HybridTextIndex, load_text_records, save_text_records
from powermind_rag.verifier import LettuceClaimVerifier
from powermind_rag.visual_understanding import (
    GeminiVisualPageAnalyzer,
    NvidiaFirstVisualPageAnalyzer,
    NvidiaVisualPageAnalyzer,
)


NOT_FOUND = "Not found in the document."
FALLBACK_NOT_FOUND = "Fallback: Not found in the document."
MAX_VISUAL_EVIDENCE_PAGES = 1
MAX_IMAGE_FALLBACK_PAGES = 3
MAX_IMAGE_GENERATION_CHARS_PER_CHUNK = 700
MAX_TEXT_GENERATION_CHARS_PER_CHUNK = 2500
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
        self.embedder = DenseEmbedder(
            self.config.nvidia_embedding_model,
            api_key=self.config.nvidia_api_key,
            base_url=self.config.nvidia_vlm_base_url,
            batch_size=self.config.nvidia_embedding_batch_size,
            timeout_seconds=self.config.nvidia_embedding_timeout_seconds,
        )
        self.text_index = HybridTextIndex(self.embedder)
        self.visual_index: Any | None = None
        self.text_records: list[TextChunkRecord] = []
        self.generator: ChatLLM | None = None
        self.image_generator: ChatLLM | None = None
        self.relevance_grader: RelevanceGrader | None = None
        self.verifier: LettuceClaimVerifier | None = None
        self.visual_page_analyzer: (
            GeminiVisualPageAnalyzer | NvidiaFirstVisualPageAnalyzer | NvidiaVisualPageAnalyzer | None
        ) = None
        self.last_ingest_report: dict[str, object] = {}

    def ingest_pdf(
        self,
        pdf_path: Path,
        doc_type: str = "PDF document",
        section: str = "document content",
        context: str | None = None,
        metadata: dict | None = None,
    ) -> dict[str, object]:
        from powermind_rag.document import document_id_for, extract_pdf_text, render_pdf_pages

        document_id = document_id_for(pdf_path)
        context = context or pdf_path.stem.replace("_", " ")
        base_dir = self.config.storage_dir / document_id
        tables_by_page = defaultdict(str)
        visual_markdown_by_page: dict[int, str] = {}
        visual_failures: list[dict[str, object]] = []
        should_render_pages = bool(self.config.mistral_api_key) or self.config.enable_visual_understanding
        image_paths = []
        if should_render_pages:
            image_paths = render_pdf_pages(pdf_path, base_dir / "pages")
        if self.config.enable_visual_understanding:
            visual_markdown_by_page, visual_failures = self._load_or_analyze_visual_pages(
                image_paths=image_paths,
                document_id=document_id,
                doc_type=doc_type,
                section=section,
                context=context,
                cache_path=base_dir / "visual_page_analysis.json",
            )
            self._unload_visual_page_analyzer()
        if bool(self.config.mistral_api_key):
            ocr = MistralTableOCR(
                self.config.mistral_api_key,
                self.config.mistral_ocr_model,
                server_url=self.config.mistral_server_url,
                timeout_ms=self.config.mistral_timeout_ms,
            )
            for table in ocr.extract_markdown_tables(image_paths):
                tables_by_page[table.page_number] += table.markdown + "\n\n"
        if self.config.enable_colpali_visual_index:
            self._visual_index().build(image_paths, document_id=document_id, metadata=metadata or {})
            if self.visual_index is not None:
                self.visual_index.save_document_records(document_id, base_dir / "visual_records.json")
                self.visual_index.unload_model()

        use_rule_chunking = self.config.chunking_provider in {"rules", "local-rules"}
        chunker = None if self.config.local_only or use_rule_chunking else PropositionChunker(self._chunking_llm())
        records: list[TextChunkRecord] = []
        chunk_counter = 1
        for page in extract_pdf_text(pdf_path):
            table_markdown = tables_by_page[page.page_number]
            visual_markdown = visual_markdown_by_page.get(page.page_number, "")
            if chunker is None:
                propositions = _local_propositions(
                    _combined_text(page.text, table_markdown, visual_markdown)
                )
            else:
                try:
                    propositions = chunker.chunk(
                        page_text=_combined_text(page.text, visual_markdown),
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
                    propositions = _local_propositions(
                        _combined_text(page.text, table_markdown, visual_markdown)
                    )
            for proposition in propositions:
                chunk_label = f"c{chunk_counter}"
                chunk_id = f"{document_id}:{chunk_label}"
                prefix = (
                    f"This chunk is from {doc_type}, {section}, describing {context}. "
                    "It may include PDF text, OCR table text, or visual page analysis."
                )
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
        self.last_ingest_report = {
            "document_id": document_id,
            "pdf": str(pdf_path),
            "text_records": len(records),
            "visual_pages_succeeded": len(visual_markdown_by_page),
            "visual_pages_failed": len(visual_failures),
            "visual_failures": visual_failures,
        }
        return self.last_ingest_report

    def load_from_storage(self) -> None:
        text_records: list[TextChunkRecord] = []
        visual_records = []
        for text_path in self.config.storage_dir.glob("*/text_records.json"):
            if (
                not self.config.load_imported_records
                and text_path.parent.name.endswith("_embeddings_import")
            ):
                continue
            records = load_text_records(text_path)
            records = self._ensure_current_text_embeddings(records, text_path)
            text_records.extend(records)
        if self.config.enable_colpali_visual_index and self.config.enable_query_visual_retrieval:
            from powermind_rag.visual_index import load_visual_records

            for visual_path in self.config.storage_dir.glob("*/visual_records.json"):
                if (
                    not self.config.load_imported_records
                    and visual_path.parent.name.endswith("_embeddings_import")
                ):
                    continue
                visual_records.extend(load_visual_records(visual_path))
        if not text_records:
            raise RuntimeError(f"No ingested records found under {self.config.storage_dir}.")
        self.text_records = text_records
        if text_records:
            self.text_index.build(text_records)
        if visual_records:
            self._visual_index().load_records(visual_records)

    def _ensure_current_text_embeddings(
        self,
        records: list[TextChunkRecord],
        text_path: Path,
    ) -> list[TextChunkRecord]:
        if not records:
            return records

        expected_dim = self.embedder.dimension
        current_dims = {len(record.embedding) for record in records if record.embedding}
        if current_dims == {expected_dim}:
            return records

        print(
            f"Embedding dimension mismatch in {text_path}: found {sorted(current_dims)} "
            f"but current embedder {self.config.nvidia_embedding_model} uses {expected_dim}. "
            "Re-embedding stored chunks with NVIDIA and saving them back...",
            flush=True,
        )
        texts = [record.text for record in records]
        embeddings = self.embedder.encode_passages(texts)
        updated = [
            replace(record, embedding=embedding.tolist())
            for record, embedding in zip(records, embeddings)
        ]
        save_text_records(updated, text_path)
        print(f"Re-embedded {len(updated)} chunks in {text_path}.", flush=True)
        return updated

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
        text_page_hints = _ranked_text_pages(text_hits, MAX_IMAGE_FALLBACK_PAGES)
        visual_start = perf_counter()
        if (
            self.config.local_only
            or not self.config.enable_colpali_visual_index
            or self.visual_index is None
            or not self.config.enable_query_visual_retrieval
        ):
            visual_hits = []
        else:
            visual_hits = self.visual_index.search(query, self.config.visual_top_k)
        timings["visual_retrieval"] = perf_counter() - visual_start
        final_fusion_start = perf_counter()
        candidates = reciprocal_rank_fusion([text_hits, visual_hits], k=self.config.rrf_k)[
            : final_top_k
        ]
        timings["final_rrf"] = perf_counter() - final_fusion_start

        if self.config.relevance_provider in {"none", "lexical", "local"}:
            graded = _lexical_crag_grade(query, candidates)
        else:
            grade_start = perf_counter()
            try:
                graded = self._relevance().grade(query, candidates)
            except RuntimeError as exc:
                if not self.config.allow_lexical_crag_fallback:
                    raise RuntimeError(
                        "CRAG relevance grading failed and lexical fallback is disabled. "
                        "Fix POWERMIND_RELEVANCE_PROVIDER/Gemini keys, or set "
                        "POWERMIND_ALLOW_LEXICAL_CRAG_FALLBACK=1 only for emergency degraded runs."
                    ) from exc
                print(
                    f"CRAG LLM relevance grading failed; using emergency lexical CRAG fallback. "
                    f"Reason: {exc}",
                    flush=True,
                )
                graded = _lexical_crag_grade(query, candidates)
            timings["relevance_grading"] = perf_counter() - grade_start
        supported = [chunk for chunk, score in graded if score >= self.config.relevance_threshold]
        if not supported:
            image_answer = self._generate_image_fallback(query, candidates)
            if image_answer.strip() != NOT_FOUND:
                return finalize(
                    text=image_answer,
                    retrieved=candidates[:MAX_IMAGE_FALLBACK_PAGES],
                    is_fallback=False,
                )
            return finalize(text=NOT_FOUND, retrieved=candidates, is_fallback=False)

        text_evidence = [chunk for chunk in supported if chunk.modality == "text"]
        visual_evidence = (
            _related_visual_evidence(
                candidates,
                text_evidence,
                text_page_hints,
                self.config.storage_dir,
            )
            if self._can_generate_from_images()
            else []
        )
        if not text_evidence and not self._can_generate_from_images():
            return finalize(text=FALLBACK_NOT_FOUND, retrieved=supported, is_fallback=True)

        try:
            generation_start = perf_counter()
            answer = self._generate_grounded_answer(query, text_evidence + visual_evidence)
            timings["generation"] = perf_counter() - generation_start
        except Exception as exc:
            timings["generation"] = perf_counter() - generation_start
            raise exc
        if answer.strip() == NOT_FOUND:
            image_answer = self._generate_image_fallback(query, candidates)
            if image_answer.strip() != NOT_FOUND:
                return finalize(
                    text=image_answer,
                    retrieved=candidates[:MAX_IMAGE_FALLBACK_PAGES],
                    is_fallback=False,
                )
            return finalize(text=NOT_FOUND, retrieved=text_evidence, is_fallback=False)

        if self.config.enable_verification:
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
        return finalize(
            text=answer,
            retrieved=text_evidence,
            verifier_report={"skipped": "POWERMIND_ENABLE_VERIFICATION is not enabled."},
        )

    def retrieve_evidence(
        self,
        query: str,
        top_k: int | None = None,
        use_relevance: bool = True,
    ) -> tuple[list[RetrievedChunk], dict[str, float]]:
        """Retrieve grounded evidence without generating the final answer.

        This is the path to expose over MCP when the MCP host's LLM should do
        the final synthesis.
        """
        timings = {name: 0.0 for name in TIMING_KEYS}
        total_start = perf_counter()

        def finish(chunks: list[RetrievedChunk]) -> tuple[list[RetrievedChunk], dict[str, float]]:
            timings["total"] = perf_counter() - total_start
            limit = top_k or self.config.final_top_k
            return chunks[:limit], dict(timings)

        if not self.text_records:
            load_start = perf_counter()
            self.load_from_storage()
            timings["storage_load"] = perf_counter() - load_start
        expansion_start = perf_counter()
        expanded_query, keyword_terms = _expand_query(query)
        timings["query_expansion"] = perf_counter() - expansion_start

        text_top_k = max(self.config.text_top_k, top_k or 0)
        final_top_k = max(self.config.final_top_k, top_k or 0)

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
        if (
            self.config.local_only
            or not self.config.enable_colpali_visual_index
            or self.visual_index is None
            or not self.config.enable_query_visual_retrieval
        ):
            visual_hits = []
        else:
            visual_hits = self.visual_index.search(query, self.config.visual_top_k)
        timings["visual_retrieval"] = perf_counter() - visual_start

        final_fusion_start = perf_counter()
        candidates = reciprocal_rank_fusion([text_hits, visual_hits], k=self.config.rrf_k)[:final_top_k]
        timings["final_rrf"] = perf_counter() - final_fusion_start

        if not use_relevance or self.config.relevance_provider in {"none", "local"}:
            return finish(candidates)

        if self.config.relevance_provider in {"lexical"}:
            graded = _lexical_crag_grade(query, candidates)
        else:
            grade_start = perf_counter()
            try:
                graded = self._relevance().grade(query, candidates)
            except RuntimeError:
                if not self.config.allow_lexical_crag_fallback:
                    raise
                graded = _lexical_crag_grade(query, candidates)
            timings["relevance_grading"] = perf_counter() - grade_start

        supported = [chunk for chunk, score in graded if score >= self.config.relevance_threshold]
        return finish(supported or candidates)

    def _generate_grounded_answer(self, query: str, chunks: list[RetrievedChunk]) -> str:
        chunks = _generation_context_chunks(chunks)
        image_paths = [
            Path(path)
            for chunk in chunks
            if chunk.modality == "image"
            for path in [chunk.metadata.get("raw_image_path")]
            if path
        ]
        trim_limit = (
            MAX_IMAGE_GENERATION_CHARS_PER_CHUNK if image_paths else MAX_TEXT_GENERATION_CHARS_PER_CHUNK
        )
        context_lines = [
            f"{chunk.citation} {_trim_generation_text(chunk.text, trim_limit)}" for chunk in chunks
        ]
        user = f"""
Answer the query using ONLY the retrieved context below.
Search deeply across every retrieved chunk for the exact entities, labels, and numbers requested by the query.
Preserve the document's visible structure: headings as headings, table data as markdown tables, bullets as bullets, and chart/infographic values as labeled bullet points.
Include every relevant value, unit, currency symbol, percentage, sign, period, footnote marker, and comparison exactly as shown.
Work through the chunks in order; if the answer is not found early, continue to later chunks before concluding.
Every factual statement and every number must have a citation in the exact format [pN:cK].
If retrieved page images are attached, read ALL visible text in the image (titles, legends, callouts, labels inside shapes, axis ticks, footnotes, table cells) and cite those findings with [pN:image].
For charts, infographics, and flowcharts, map labels to exact values, units, directions, and relationships as shown in the image.
Do not summarize away requested detail. Do not infer missing numbers or labels. Do not use outside knowledge.
If a value is unreadable or ambiguous, return {NOT_FOUND} rather than guessing.
If the context does not explicitly support the answer, return exactly: {NOT_FOUND}

QUERY:
{query}

RETRIEVED CONTEXT:
{chr(10).join(context_lines)}
""".strip()
        if image_paths:
            generator = self._image_llm()
            return generator.generate_with_images(
                system=(
                    "You are a grounded document QA model with zero hallucination tolerance. "
                    "Use only the provided text and attached page images. "
                    "Read embedded image text (titles, legends, callouts, labels inside shapes, axis ticks, tables). "
                    "Extract exact labels and numeric values from charts and infographics. "
                    "Never guess or smooth numbers."
                ),
                user=user,
                image_paths=image_paths[:MAX_VISUAL_EVIDENCE_PAGES],
                max_new_tokens=512,
            )
        generator = self._generation_llm()
        return generator.generate(
            system=(
                "You are a grounded document QA model with zero hallucination tolerance. "
                "Use only the provided text context. "
                "Never guess or smooth numbers."
            ),
            user=user,
            max_new_tokens=512,
        )

    def _generate_image_fallback(self, query: str, chunks: list[RetrievedChunk]) -> str:
        if not self._can_use_image_fallback():
            return NOT_FOUND
        fallback_chunks = chunks[:MAX_IMAGE_FALLBACK_PAGES]
        if not fallback_chunks:
            return NOT_FOUND
        image_paths = self._fallback_page_image_paths(fallback_chunks)
        if not image_paths:
            return NOT_FOUND
        page_list = ", ".join(f"p{chunk.page_number}" for chunk in fallback_chunks)
        user = f"""
Re-check the top 3 most similar pages below and answer the exact query again.
Use only the attached page images.
The attached images, when present, are in order: {page_list}.
If the answer is not explicitly visible in the pages, return exactly: {NOT_FOUND}

QUERY:
{query}
""".strip()
        generator = self._image_llm()
        return generator.generate_with_images(
            system=(
                "You are a grounded document QA model with zero hallucination tolerance. "
                "Use only the attached page images. "
                "Never guess or smooth numbers."
            ),
            user=user,
            image_paths=image_paths,
            max_new_tokens=512,
        )

    def _can_generate_from_images(self) -> bool:
        return (
            self.config.include_page_images_in_answers
            and self.config.image_generation_provider
            in {"nvidia", "gemini", "gemini_nvidia", "nvidia_gemini"}
        )

    def _can_use_image_fallback(self) -> bool:
        return (
            self.config.enable_query_vlm_fallback
            and self.config.image_generation_provider
            in {"nvidia", "gemini", "gemini_nvidia", "nvidia_gemini"}
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

    def _load_or_analyze_visual_pages(
        self,
        image_paths: list[Path],
        document_id: str,
        doc_type: str,
        section: str,
        context: str,
        cache_path: Path,
    ) -> tuple[dict[int, str], list[dict[str, object]]]:
        cached = {} if self.config.refresh_visual_understanding else _load_visual_page_analysis(cache_path)
        if cached and set(cached) == set(range(1, len(image_paths) + 1)):
            return cached, []

        analyzer = self._visual_page_analyzer()
        analyses: dict[int, str] = dict(cached)
        failures: list[dict[str, object]] = []
        for page_number, image_path in enumerate(sorted(image_paths), start=1):
            if analyses.get(page_number):
                continue
            print(
                f"Analyzing {document_id} page {page_number} with {self._visual_understanding_model_label()}...",
                flush=True,
            )
            try:
                analyses[page_number] = analyzer.analyze_page(
                    image_path=image_path,
                    page_number=page_number,
                    doc_type=doc_type,
                    section=section,
                    context=context,
                )
                _save_visual_page_analysis(cache_path, analyses)
            except Exception as exc:
                failures.append(
                    {
                        "page_number": page_number,
                        "image_path": str(image_path),
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                print(
                    f"Visual analysis failed for {document_id} page {page_number}; "
                    f"continuing ingest with PDF text and Mistral OCR only for this page. "
                    f"Reason: {type(exc).__name__}: {exc}",
                    flush=True,
                )
        _save_visual_failure_report(cache_path.with_name("visual_page_failures.json"), failures)
        return analyses, failures

    def _visual_index(self):
        if self.visual_index is None or getattr(self.visual_index, "model", None) is None:
            from powermind_rag.visual_index import ColPaliVisualIndex

            previous_records = getattr(self.visual_index, "records", []) if self.visual_index else []
            self.visual_index = ColPaliVisualIndex(
                self.config.colpali_model_name,
                device=self.device,
            )
            self.visual_index.records.extend(previous_records)
        return self.visual_index

    def _visual_page_analyzer(
        self,
    ) -> GeminiVisualPageAnalyzer | NvidiaFirstVisualPageAnalyzer | NvidiaVisualPageAnalyzer:
        if self.visual_page_analyzer is None:
            nvidia_fallback = NvidiaVisualPageAnalyzer(
                api_key=self.config.nvidia_api_key,
                model_name=self.config.nvidia_vlm_model,
                base_url=self.config.nvidia_vlm_base_url,
                max_tokens=self.config.nvidia_vlm_max_tokens,
                image_max_bytes=self.config.nvidia_vlm_image_max_bytes,
                image_max_side=self.config.nvidia_vlm_image_max_side,
                timeout_seconds=self.config.nvidia_vlm_timeout_seconds,
            )
            if self.config.visual_understanding_provider in {"gemini", "gemini_nvidia"}:
                self.visual_page_analyzer = GeminiVisualPageAnalyzer(
                    api_keys=self.config.gemini_api_keys,
                    model_name=self.config.gemini_relevance_model,
                    fallback=nvidia_fallback,
                    max_tokens=self.config.nvidia_vlm_max_tokens,
                )
            elif self.config.visual_understanding_provider == "nvidia_gemini":
                gemini_fallback = GeminiVisualPageAnalyzer(
                    api_keys=self.config.gemini_api_keys,
                    model_name=self.config.gemini_relevance_model,
                    fallback=None,
                    max_tokens=self.config.nvidia_vlm_max_tokens,
                )
                self.visual_page_analyzer = NvidiaFirstVisualPageAnalyzer(
                    primary=nvidia_fallback,
                    fallback=gemini_fallback,
                )
            elif self.config.visual_understanding_provider == "nvidia":
                self.visual_page_analyzer = nvidia_fallback
            else:
                raise RuntimeError(
                    "Unsupported POWERMIND_VISUAL_UNDERSTANDING_PROVIDER. Use 'nvidia_gemini', 'gemini', 'gemini_nvidia', or 'nvidia'."
                )
        return self.visual_page_analyzer

    def _visual_understanding_model_label(self) -> str:
        if self.config.visual_understanding_provider == "nvidia_gemini":
            return f"{self.config.nvidia_vlm_model} -> {self.config.gemini_relevance_model}"
        if self.config.visual_understanding_provider in {"gemini", "gemini_nvidia"}:
            return f"{self.config.gemini_relevance_model} -> {self.config.nvidia_vlm_model}"
        return self.config.nvidia_vlm_model

    def _unload_visual_page_analyzer(self) -> None:
        analyzer = self.visual_page_analyzer
        if analyzer is not None and hasattr(analyzer, "unload_model"):
            analyzer.unload_model()
            self.visual_page_analyzer = None

    def _generation_llm(self) -> ChatLLM:
        if self.generator is None:
            if self.config.generation_provider == "groq":
                self.generator = GroqChatLLM(
                    api_key=self.config.groq_api_key,
                    model_name=self.config.groq_generation_model,
                )
            elif self.config.generation_provider == "openrouter":
                self.generator = OpenRouterChatLLM(
                    api_key=self.config.openrouter_api_key,
                    model_name=self.config.openrouter_generation_model,
                    base_url=self.config.openrouter_base_url,
                    http_referer=self.config.openrouter_http_referer,
                    app_title=self.config.openrouter_app_title,
                )
            elif self.config.generation_provider == "nvidia":
                self.generator = NvidiaChatLLM(
                    api_key=self.config.nvidia_api_key,
                    model_name=self.config.nvidia_generation_model,
                    base_url=self.config.nvidia_vlm_base_url,
                )
            elif self.config.generation_provider == "gemini":
                self.generator = GeminiChatLLM(
                    api_key=self.config.gemini_api_keys,
                    model_name=self.config.gemini_relevance_model,
                )
            else:
                raise RuntimeError(
                    "Unsupported POWERMIND_GENERATION_PROVIDER. Use 'groq', 'openrouter', 'gemini', or 'nvidia'."
                )
        return self.generator

    def _image_llm(self) -> ChatLLM:
        if self.image_generator is None:
            nvidia = NvidiaChatLLM(
                api_key=self.config.nvidia_api_key,
                model_name=self.config.nvidia_generation_model,
                base_url=self.config.nvidia_vlm_base_url,
            )
            if self.config.image_generation_provider == "nvidia":
                self.image_generator = nvidia
            elif self.config.image_generation_provider == "gemini":
                self.image_generator = GeminiChatLLM(
                    api_key=self.config.gemini_api_keys,
                    model_name=self.config.gemini_relevance_model,
                )
            elif self.config.image_generation_provider == "gemini_nvidia":
                gemini = GeminiChatLLM(
                    api_key=self.config.gemini_api_keys,
                    model_name=self.config.gemini_relevance_model,
                )
                self.image_generator = FallbackChatLLM(gemini, nvidia)
            elif self.config.image_generation_provider == "nvidia_gemini":
                gemini = GeminiChatLLM(
                    api_key=self.config.gemini_api_keys,
                    model_name=self.config.gemini_relevance_model,
                )
                self.image_generator = FallbackChatLLM(nvidia, gemini)
            else:
                raise RuntimeError(
                    "Unsupported POWERMIND_IMAGE_PROVIDER. Use 'nvidia_gemini', 'gemini_nvidia', 'gemini', or 'nvidia'."
                )
        return self.image_generator

    def _chunking_llm(self) -> ChatLLM:
        if self.config.chunking_provider == "groq":
            primary = GroqChatLLM(
                api_key=self.config.groq_api_key,
                model_name=self.config.groq_chunking_model,
            )
            if self.config.chunking_fallback_provider == "gemini":
                fallback = GeminiChatLLM(
                    api_key=self.config.gemini_api_keys,
                    model_name=self.config.gemini_chunking_model,
                )
                return FallbackChatLLM(primary, fallback)
            return primary
        if self.config.chunking_provider == "gemini":
            return GeminiChatLLM(
                api_key=self.config.gemini_api_keys,
                model_name=self.config.gemini_chunking_model,
            )
        raise RuntimeError("Unsupported POWERMIND_CHUNKING_PROVIDER. Use 'groq', 'gemini', or 'rules'.")

    def _relevance(self) -> RelevanceGrader:
        if self.relevance_grader is None:
            if self.config.relevance_provider == "gemini":
                api_key = [
                    key
                    for key in self.config.gemini_api_keys
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

    def _lazy_image_fallback_pages(
        self,
        candidates: list[RetrievedChunk],
        text_evidence: list[RetrievedChunk],
        text_page_hints: list[tuple[str, int]],
    ) -> list[RetrievedChunk]:
        if not self._can_use_image_fallback():
            return []
        return _related_visual_evidence(
            candidates,
            text_evidence,
            text_page_hints,
            self.config.storage_dir,
            limit=MAX_IMAGE_FALLBACK_PAGES,
        )

    def _fallback_page_image_paths(self, chunks: list[RetrievedChunk]) -> list[Path]:
        seen_pages: set[tuple[str, int]] = set()
        image_paths: list[Path] = []
        for chunk in chunks:
            page_key = (chunk.document_id, chunk.page_number)
            if page_key in seen_pages:
                continue
            seen_pages.add(page_key)
            image_path = self.config.storage_dir / chunk.document_id / "pages" / f"page_{chunk.page_number:04d}.png"
            if image_path.exists():
                image_paths.append(image_path)
        return image_paths


def _local_propositions(text: str) -> list[str]:
    if not text.strip():
        return []
    propositions: list[str] = []
    for block in _markdown_blocks(text):
        if _looks_like_markdown_table(block):
            propositions.extend(_table_propositions(block))
            continue
        structured = _structured_bullet_propositions(block)
        if structured:
            propositions.extend(structured)
            continue
        clean = re.sub(r"\s+", " ", block).strip()
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", clean)
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


def _structured_bullet_propositions(block: str) -> list[str]:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if len(lines) < 2:
        return []
    heading = ""
    facts: list[str] = []
    for line in lines:
        if line.startswith("#"):
            heading = re.sub(r"^#+\s*", "", line).strip()
            continue
        if line.startswith(("-", "*")):
            fact = line[1:].strip()
            if len(fact) >= 20:
                facts.append(f"{heading}: {fact}" if heading else fact)
    return facts


def _markdown_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    current_is_table: bool | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            if current:
                blocks.append("\n".join(current).strip())
                current = []
                current_is_table = None
            continue
        is_table = "|" in line and line.count("|") >= 2
        if current and current_is_table is not None and is_table != current_is_table:
            blocks.append("\n".join(current).strip())
            current = []
        current.append(line)
        current_is_table = is_table
    if current:
        blocks.append("\n".join(current).strip())
    return [block for block in blocks if block]


def _looks_like_markdown_table(block: str) -> bool:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    table_lines = [line for line in lines if "|" in line and line.count("|") >= 2]
    return len(table_lines) >= 2


def _table_propositions(table: str, max_chars: int = 1200) -> list[str]:
    lines = [line.strip() for line in table.splitlines() if line.strip()]
    row_facts = _markdown_table_row_facts(lines)
    if row_facts:
        return row_facts
    if len("\n".join(lines)) <= max_chars:
        return ["\n".join(lines)]
    header = lines[:2] if len(lines) >= 2 else lines[:1]
    rows = lines[2:] if len(lines) >= 2 else []
    chunks: list[str] = []
    current = list(header)
    for row in rows:
        candidate = "\n".join(current + [row])
        if len(candidate) > max_chars and len(current) > len(header):
            chunks.append("\n".join(current))
            current = list(header)
        current.append(row)
    if current:
        chunks.append("\n".join(current))
    return chunks


def _markdown_table_row_facts(lines: list[str]) -> list[str]:
    table_lines = [line for line in lines if "|" in line and line.count("|") >= 2]
    if len(table_lines) < 2:
        return []
    title = ""
    for line in lines:
        if line.startswith("#"):
            title = re.sub(r"^#+\s*", "", line).strip()
            break
    parsed = [_split_markdown_row(line) for line in table_lines]
    parsed = [row for row in parsed if row and not _is_markdown_separator(row)]
    if len(parsed) < 2:
        return []
    header = parsed[0]
    facts = []
    for row in parsed[1:]:
        width = min(len(header), len(row))
        pairs = [
            f"{header[index]}={row[index]}"
            for index in range(width)
            if header[index] and row[index]
        ]
        if len(pairs) >= 2:
            prefix = f"{title}: " if title else "Table row: "
            facts.append(prefix + "; ".join(pairs))
    return facts


def _split_markdown_row(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    cells = re.split(r"(?<!\\)\|", stripped)
    return [cell.replace("\\|", "|").strip() for cell in cells]


def _is_markdown_separator(row: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in row if cell.strip())


def _combined_text(*parts: str) -> str:
    return "\n\n".join(part for part in parts if part and part.strip())


def _load_visual_page_analysis(path: Path) -> dict[int, str]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {int(page_number): text for page_number, text in payload.items() if text}


def _save_visual_page_analysis(path: Path, analyses: dict[int, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {str(page_number): text for page_number, text in sorted(analyses.items())}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _save_visual_failure_report(path: Path, failures: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(failures, indent=2, ensure_ascii=False), encoding="utf-8")


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
    lower = query.lower()
    if "ebidta" in lower:
        terms.append("EBITDA")
    if "cat" in lower:
        terms.extend(["CAT", "CAT (FFO)", "FFO"])
    if "ffo" in lower:
        terms.extend(["Fund Flow from Operations", "CAT (FFO)"])
    if "cagr" in lower:
        terms.extend(["CAGR", "Compounded Annual Growth Rate"])
    deduped_terms = list(dict.fromkeys(terms))
    return query, deduped_terms


def _lexical_crag_grade(query: str, chunks: list[RetrievedChunk]) -> list[tuple[RetrievedChunk, float]]:
    _, terms = _expand_query(query)
    normalized_terms = [term.lower() for term in terms if term.strip()]
    graded = []
    for chunk in chunks:
        text = chunk.text.lower()
        matched = sum(1 for term in normalized_terms if term.lower() in text)
        score = min(1.0, matched / max(3, len(normalized_terms) * 0.35))
        if chunk.modality == "image" and any(term in text for term in ("visual", "image")):
            score = max(score, 0.2)
        graded.append((chunk, score))
    return graded


def _related_visual_evidence(
    candidates: list[RetrievedChunk],
    text_evidence: list[RetrievedChunk],
    page_hints: list[tuple[str, int]] | None = None,
    storage_dir: Path | None = None,
    limit: int = MAX_VISUAL_EVIDENCE_PAGES,
) -> list[RetrievedChunk]:
    storage_dir = storage_dir or Path("storage")
    evidence_pages = list(page_hints or [])
    for chunk in text_evidence:
        page_key = (chunk.document_id, chunk.page_number)
        if page_key not in evidence_pages:
            evidence_pages.append(page_key)
    visuals = [chunk for chunk in candidates if chunk.modality == "image"]
    if not evidence_pages:
        return visuals[:limit]

    visual_by_page: dict[tuple[str, int], RetrievedChunk] = {}
    for visual in visuals:
        key = (visual.document_id, visual.page_number)
        if key not in visual_by_page:
            visual_by_page[key] = visual

    selected: list[RetrievedChunk] = []
    for document_id, page_number in evidence_pages:
        key = (document_id, page_number)
        if key in visual_by_page:
            selected.append(visual_by_page[key])
            continue
        image_path = storage_dir / document_id / "pages" / f"page_{page_number:04d}.png"
        if not image_path.exists():
            continue
        selected.append(
            RetrievedChunk(
                id=f"{document_id}:p{page_number}:image",
                text=f"Page image evidence attached for text evidence on page {page_number}.",
                document_id=document_id,
                page_number=page_number,
                modality="image",
                rank=0,
                score=0.0,
                metadata={"chunk_label": "image", "raw_image_path": str(image_path)},
            )
        )
        if len(selected) >= limit:
            break
    if selected:
        return selected[:limit]
    return visuals[:limit]


def _generation_context_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    text_chunks = [chunk for chunk in chunks if chunk.modality == "text"]
    image_chunks = [chunk for chunk in chunks if chunk.modality == "image"]
    return text_chunks[:3] + image_chunks[:MAX_VISUAL_EVIDENCE_PAGES]


def _trim_generation_text(text: str, limit: int) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3].rstrip() + "..."


def _ranked_text_pages(
    text_hits: list[RetrievedChunk],
    limit: int,
) -> list[tuple[str, int]]:
    pages: list[tuple[str, int]] = []
    for chunk in text_hits:
        page_key = (chunk.document_id, chunk.page_number)
        if page_key not in pages:
            pages.append(page_key)
        if len(pages) >= limit:
            break
    return pages
