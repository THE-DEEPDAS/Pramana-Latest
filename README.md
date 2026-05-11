# Pramana

Pramana is an explainable multimodal RAG system for high-stakes document QA. It is designed for reports, board documents, financial decks, and visually dense PDFs where important facts may appear in normal text, tables, diagrams, charts, infographics, or page layout.

The production pipeline lives in `service/src/powermind_rag` and is API-first by default: NVIDIA-hosted embeddings, Mistral OCR, Gemini/NVIDIA VLM page understanding, Gemini CRAG relevance grading, and NVIDIA/Gemini final visual fallback.

## What Pramana Does

- Ingests PDF documents into local JSON records under `service/storage`.
- Extracts normal PDF text.
- Runs Mistral OCR for table and layout-heavy page content.
- Runs visual page understanding during ingestion:
  - Ingestion VLM order: Gemini first, NVIDIA Phi fallback.
  - Failed pages are recorded in `visual_page_failures.json`.
- Embeds chunks with NVIDIA `nvidia/nv-embed-v1`.
- Retrieves with BM25, keyword search, dense FAISS search, and Reciprocal Rank Fusion.
- Applies CRAG relevance grading before answer generation.
- Generates grounded answers with citations like `[p3:c12]`.
- If the normal pipeline returns `Not found in the document.`, performs one final page-image VLM check:
  - Query fallback order: NVIDIA Phi first, Gemini fallback.

## Project Links

- [Presentation](Presentation.pdf)
- [Architecture Diagram](Architecture.jpeg)
- [Frontend Docs](docs/frontend.md)
- [Backend Docs](docs/backend.md)
- [AI Workflow Docs](docs/ai_workflow.md)

![Pramana Architecture](Architecture.jpeg)

## Current Architecture

```text
PDF
 |-- normal text extraction
 |-- page rendering
 |-- Mistral OCR
 |-- Gemini page analysis -> NVIDIA Phi fallback
 |
chunk factual propositions
 |
NVIDIA nv-embed-v1 embeddings
 |
service/storage/<document_id>/text_records.json
 |
query
 |-- BM25
 |-- keyword
 |-- NVIDIA dense query embedding + FAISS
 |-- RRF
 |-- Gemini CRAG relevance grading
 |-- grounded answer generation
 |-- final VLM page fallback when not found
```

## Repository Layout

```text
PowerMind/
|-- powermind_rag/                  # repo-root shim so python -m uses service source
|-- service/
|   |-- src/powermind_rag/          # production Pramana RAG package
|   |-- data/                       # input PDFs
|   |-- storage/                    # generated text records and page analysis
|   |-- tests/
|   |-- README.md
|-- backend/                        # compatibility FastAPI app
|-- frontend/                       # Next.js UI
|-- scripts/                        # runners and smoke scripts
|-- Presentation.pdf
|-- Architecture.jpeg
```

The old backend RAG v2/LangGraph/Pinecone path has been removed. The main runnable pipeline is the service package.

## Environment

The repo-root `.env` is loaded automatically. Important values:

```env
POWERMIND_STORAGE_DIR="D:\PowerMind\service\storage"
POWERMIND_DEVICE="api"

NVIDIA_KEY="..."
NVIDIA_EMBEDDING_MODEL="nvidia/nv-embed-v1"
NVIDIA_VLM_MODEL="microsoft/phi-4-multimodal-instruct"
NVIDIA_GENERATION_MODEL="microsoft/phi-4-multimodal-instruct"
NVIDIA_VLM_BASE_URL="https://integrate.api.nvidia.com/v1"

MISTRAL_API_KEY="..."
MISTRAL_SERVER_URL="https://api.mistral.ai"

GEMINI_API_KEY_1="..."
GEMINI_API_KEY_2="..."
GEMINI_API_KEY_3="..."
GEMINI_API_KEY_4="..."
GEMINI_API_KEY_5="..."
GEMINI_API_KEY_6="..."
GEMINI_RELEVANCE_MODEL="gemini-2.5-flash"

POWERMIND_ENABLE_VISUAL_UNDERSTANDING="true"
POWERMIND_VISUAL_UNDERSTANDING_PROVIDER="gemini_nvidia"
POWERMIND_IMAGE_PROVIDER="nvidia_gemini"
POWERMIND_ENABLE_QUERY_VLM_FALLBACK="1"
POWERMIND_RELEVANCE_PROVIDER="gemini"
POWERMIND_ALLOW_LEXICAL_CRAG_FALLBACK="0"

POWERMIND_ENABLE_COLPALI_VISUAL_INDEX="0"
```

`POWERMIND_ENABLE_COLPALI_VISUAL_INDEX` is optional and off by default. Turning it on loads the optional ColPali/byaldi visual index. Keep it off for the API-first deployment.

## Install

From the service folder:

```powershell
cd D:\PowerMind\service
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

From the repo root, `python -m powermind_rag.cli ...` uses `service/src/powermind_rag` through the root shim.

Verify module resolution:

```powershell
cd D:\PowerMind
python -c "import importlib.util; print(importlib.util.find_spec('powermind_rag.cli').origin)"
```

Expected:

```text
D:\PowerMind\service\src\powermind_rag\cli.py
```

## Ingest

Single PDF:

```powershell
cd D:\PowerMind
python -m powermind_rag.cli ingest "D:\PowerMind\service\data\AEL_Earnings_Presentation_Q2-FY26_copy.pdf"
```

All PDFs in `service/data`:

```powershell
cd D:\PowerMind
python -m powermind_rag.cli ingest-dir "D:\PowerMind\service\data"
```

Ingestion writes:

```text
service/storage/<document_id>/text_records.json
service/storage/<document_id>/visual_page_analysis.json
service/storage/<document_id>/visual_page_failures.json
```

## Ask

```powershell
cd D:\PowerMind
python -m powermind_rag.cli ask "What is the Adani Family's equity stake in AEL as shown in the portfolio structure diagram?" --show-timings
```

## MCP Server

Pramana can run as an MCP server for local or remote MCP hosts. The preferred tool is
`retrieve_evidence`: it returns cited evidence chunks and an answering contract, while the
LLM in the calling host performs the final inference.

Install and sync with uv:

```powershell
cd D:\PowerMind
uv sync --project service
```

Run as a remote FastMCP HTTP server:

```powershell
cd D:\PowerMind
uv run --project service fastmcp run service\src\powermind_rag\mcp_server.py --transport http --host 0.0.0.0 --port 8000
```

MCP clients should connect to:

```text
http://localhost:8000/mcp/
```

Run as a local stdio MCP server:

```powershell
cd D:\PowerMind
uv run --project service fastmcp run service\src\powermind_rag\mcp_server.py --transport stdio
```

You can also run the module directly:

```powershell
cd D:\PowerMind
uv run --project service python -m powermind_rag.mcp_server --transport http --host 0.0.0.0 --port 8000
```

Available MCP capabilities:

- `retrieve_evidence(query, top_k, use_relevance)`: returns retrieved text/image evidence with citations for host-side answering.
- `ingest_pdf(pdf_path, doc_type, section, context)`: ingests a PDF into Pramana storage.
- `list_documents()`: lists stored documents.
- `answer_from_pramana_evidence(question)`: prompt template that tells the host to retrieve evidence and answer only from it.

## Batch Questions

```powershell
cd D:\PowerMind
python -m powermind_rag.cli ask-batch --output service\outputs\qa_results.md --json-output service\outputs\qa_results.json
```

## Notes

- No local model is required in the default deployment path.
- Optional local components remain in the codebase for earlier experiments and future toggles.
- Generated Python caches are intentionally not kept.
- Stored embeddings are auto-migrated when the configured embedding model changes.
