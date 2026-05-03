# PowerMind Multimodal RAG

Strict implementation of the requested architecture:

- Dual ingestion:
  - Visual pages rendered to images, embedded with ColPali through `byaldi`, and stored in FAISS.
  - Text plus Mistral OCR table Markdown converted into LLM-generated atomic propositions.
- Dual indexing:
  - Visual FAISS page index.
  - Hybrid text index with BM25 plus E5 Small dense FAISS.
- Retrieval:
  - Visual retrieval.
  - BM25 retrieval.
  - Dense retrieval.
  - Reciprocal Rank Fusion using `1 / (60 + rank)` with no normalization or weighted averaging.
- CRAG:
  - Relevance grader before generation.
  - LettuceDetect after generation.
- Generation:
  - Local Qwen only.
  - Citations like `[p3:c12]`.
  - Unsupported answers return `Not found in the document.`

## Runtime Requirements

Use the GPU conda environment created for the RTX 5050 setup:

```cmd
conda activate powermind_rtx5050
```

This project defaults to GPU execution:

```cmd
set POWERMIND_DEVICE=cuda
set POWERMIND_CUDA_ARCH=sm_120
```

For CPU execution:

```cmd
set POWERMIND_DEVICE=cpu
```

Your RTX 5050 laptop GPU uses compute capability `sm_120`, so the PyTorch build must be new enough to support that architecture. If CUDA is not available and `POWERMIND_DEVICE` is still `cuda`, the pipeline fails closed instead of silently falling back to CPU.

Install dependencies inside `powermind_rtx5050`:

```cmd
conda create -n powermind_rtx5050 python=3.11 pip -y
conda activate powermind_rtx5050
python -m pip install --upgrade pip setuptools wheel
python -m pip install torch==2.10.0+cu128 torchvision==0.25.0+cu128 torchaudio==2.10.0+cu128 --index-url https://download.pytorch.org/whl/cu128
python -m pip install -r requirements.txt
python -m pip install -e . --no-deps
```

If `torchvision` fails with `RuntimeError: operator torchvision::nms does not exist`, reinstall a matching PyTorch and torchvision pair. For example, if `pip show torchvision` says `Requires-Dist: torch (==2.10.0)`, run:

```cmd
python -m pip install --force-reinstall torch==2.10.0+cu128 torchvision==0.25.0+cu128 torchaudio==2.10.0+cu128 --index-url https://download.pytorch.org/whl/cu128
python -m pip install --force-reinstall "transformers>=5.7.0,<6.0.0" "sentence-transformers>=5.4.1,<6.0.0"
```

For local-only runs that do not send document pages or chunks to external OCR/grading services:

```cmd
set POWERMIND_LOCAL_ONLY=1
set PYTHONDONTWRITEBYTECODE=1
```

Set Mistral OCR key:

```cmd
set MISTRAL_API_KEY=...
```

Set Gemini CRAG relevance grading keys and model:

```cmd
set POWERMIND_RELEVANCE_PROVIDER=gemini
set GEMINI_API_KEY=...
set GEMINI_API_KEY_2=...
set GEMINI_RELEVANCE_MODEL=gemini-2.5-flash
```

Proposition embeddings use the local E5 Small model by default:

```cmd
set POWERMIND_DENSE_MODEL=E5_Small
```

The `.env` file is loaded automatically.

Make sure `QWEN_MODEL_PATH` points to a complete local Qwen model.

Qwen 2.5 7B Instruct is suitable for final grounded text generation. It is text-only, so it cannot read chart pixels directly; chart/image facts must first be converted into textual evidence by the ingestion path. If only a retrieved image page is available and no supported text evidence exists, the answer is `Fallback: Not found in the document.`

## Usage

### One-Time Ingestion

Run this once for all PDFs in `data`. It creates stored records under `storage/`.

```cmd
conda activate powermind_rtx5050
set POWERMIND_LOCAL_ONLY=1
set PYTHONDONTWRITEBYTECODE=1
python -m powermind_rag.cli ingest-dir .\data --doc-type "AEL disclosure pack" --section "Q2 FY26 and H1-26 results" --context "business segments, consolidated income, EBITDA drivers, and airport performance"
```

### Ask Queries After Ingestion

This reuses the stored embeddings and records. Do not ingest again unless the PDFs change.

```cmd
conda activate powermind_rtx5050
set POWERMIND_LOCAL_ONLY=1
set PYTHONDONTWRITEBYTECODE=1
python -m powermind_rag.cli ask "What is the consolidated total income in H1-26?"
```

Add `--show-timings` to print the component-wise response-time breakdown for the same query.

### Run The Provided Question Set

```cmd
conda activate powermind_rtx5050
set POWERMIND_LOCAL_ONLY=1
set PYTHONDONTWRITEBYTECODE=1
python -m powermind_rag.cli ask-batch --output .\outputs\qa_results.md --json-output .\outputs\qa_results.json
```

The batch command writes:

- `outputs/qa_results.md` for readable answers
- `outputs/qa_results.json` with answers, citations, retrieved chunks, fallback flags, and verifier report

### Run Test Cases from test_cases.json

The `test_cases.json` file contains categorized test questions organized by type:
- **TEXTUAL**: Factual and textual extraction questions (15 questions)
- **IMAGE**: Chart and visual data extraction questions (10 questions)
- **INFOGRAPHIC**: Infographic and visual element questions (10 questions)
- **FLOWCHART**: Process flow and hierarchy questions (10 questions)
- **TABULAR**: Table and data comparison questions (15 questions)
- **BATCH**: Default batch loop questions (5 questions)

To run the testcases and generate results, use the batch runner script. By default, it will run **3 questions from each category**:

```cmd
conda activate powermind_rtx5050
set POWERMIND_LOCAL_ONLY=1
set PYTHONDONTWRITEBYTECODE=1
<<<<<<< HEAD
set POWERMIND_STORAGE_DIR=.\storage
python ..\scripts\run_batch_from_test_cases.py
```

The script will:
1. Load all questions from `test_cases.json` organized by category
2. Execute 3 questions from each category (customizable in the script)
3. Generate two output files in `outputs/`:
   - `qa_results.md`: Human-readable markdown format with answers and citations
   - `qa_results.json`: Machine-readable JSON format with detailed metadata, timings, and verifier reports

**To customize the number of questions per category**, edit `run_batch_from_test_cases.py` and change the `max_per_category` variable:
=======
set POWERMIND_STORAGE_DIR=.\service\storage
python .\scripts\run_batch_from_test_cases.py
```

The script will:
1. Load all questions from `service/test_cases.json` organized by category
2. Execute 3 questions from each category (customizable in the script)
3. Generate two output files in `service/outputs/`:
   - `qa_results.md`: Human-readable markdown format with answers and citations
   - `qa_results.json`: Machine-readable JSON format with detailed metadata, timings, and verifier reports

**To customize the number of questions per category**, edit `scripts/run_batch_from_test_cases.py` and change the `max_per_category` variable:
>>>>>>> 67292228a7704d55a65553d6e8f1d814dd93d553

```python
max_per_category = 3  # Change this number
```

<<<<<<< HEAD
**To add more test questions**, simply add them to the appropriate section in `test_cases.json` following the same structure:
=======
**To add more test questions**, simply add them to the appropriate section in `service/test_cases.json` following the same structure:
>>>>>>> 67292228a7704d55a65553d6e8f1d814dd93d553

```json
{
  "CATEGORY_NAME": [
    {
      "id": 1,
      "question": "Your question here?",
      "source": "Document reference",
      "category": "Category name",
      "type": "Question type"
    }
  ]
}
```
