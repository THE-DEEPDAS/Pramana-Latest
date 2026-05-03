from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "service" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from powermind_rag.config import RAGConfig
from powermind_rag.pipeline import MultimodalRAGPipeline


RESULT_FIELDS = (
    "answer",
    "is_fallback",
    "citations",
    "retrieved",
    "verifier_report",
    "timings",
    "error",
)


def main() -> None:
    batch_path = Path(os.getenv("POWERMIND_TEST_CASES_PATH", ROOT / "service" / "test_cases.json"))
    out_dir = Path(os.getenv("POWERMIND_OUTPUT_DIR", ROOT / "service" / "outputs"))
    out_md = out_dir / "qa_results.md"
    out_json = out_dir / "qa_results.json"

    batch_data = json.loads(batch_path.read_text(encoding="utf-8"))
    questions = []
    max_per_category_env = os.getenv("POWERMIND_MAX_PER_CATEGORY", "").strip()
    max_per_category = int(max_per_category_env) if max_per_category_env else None
    refresh_results = os.getenv("POWERMIND_REFRESH_RESULTS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    for category, items in batch_data.items():
        if not isinstance(items, list):
            continue
        selected_items = items[:max_per_category] if max_per_category is not None else items
        for item in selected_items:
            if not isinstance(item, dict) or "question" not in item:
                continue
            questions.append((category, item))

    pipeline = MultimodalRAGPipeline(RAGConfig.from_env())
    pipeline.load_from_storage()

    out_dir.mkdir(parents=True, exist_ok=True)
    out_md.write_text("# PowerMind RAG Question Results\n\n", encoding="utf-8")
    out_json.write_text("[]", encoding="utf-8")

    results = []
    for idx, (category_group, item) in enumerate(questions, 1):
        case_id = f"{category_group}-{item['id']}"
        print(f"Processing {idx}/{len(questions)}: {case_id} ...", flush=True)
        result = (
            _answer_question(pipeline, category_group, item)
            if refresh_results or not _has_successful_result(item)
            else _existing_result(category_group, item)
        )
        results.append(result)
        _store_result_on_case(item, result)
        print(f"Answered {result['id']}: {result['answer'] or result['error']}", flush=True)
        _append_markdown_result(out_md, result)
        out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")
        batch_path.write_text(json.dumps(batch_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wrote {out_md}", flush=True)
    print(f"Wrote {out_json}", flush=True)
    print(f"Updated {batch_path}", flush=True)


def _answer_question(pipeline: MultimodalRAGPipeline, category_group: str, item: dict) -> dict:
    result_base = {
        "id": f"{category_group}-{item['id']}",
        "question": item["question"],
        "source": item.get("source", category_group),
        "category": item.get("category", category_group.title()),
        "type": item.get("type", "Unknown"),
        "category_group": category_group,
    }
    try:
        answer = pipeline.answer(item["question"])
        return {
            **result_base,
            "answer": answer.text,
            "is_fallback": answer.is_fallback,
            "citations": [chunk.citation for chunk in answer.retrieved],
            "retrieved": [_retrieved_chunk_dict(chunk) for chunk in answer.retrieved],
            "verifier_report": answer.verifier_report,
            "timings": answer.timings,
            "error": None,
        }
    except Exception as exc:
        return {
            **result_base,
            "answer": "",
            "is_fallback": True,
            "citations": [],
            "retrieved": [],
            "verifier_report": {},
            "timings": {},
            "error": f"{type(exc).__name__}: {exc}",
        }


def _has_successful_result(item: dict) -> bool:
    return bool(item.get("answer")) and item.get("error") in {None, ""}


def _existing_result(category_group: str, item: dict) -> dict:
    return {
        "id": f"{category_group}-{item['id']}",
        "question": item["question"],
        "source": item.get("source", category_group),
        "category": item.get("category", category_group.title()),
        "type": item.get("type", "Unknown"),
        "category_group": category_group,
        "answer": item.get("answer", ""),
        "is_fallback": bool(item.get("is_fallback")),
        "citations": item.get("citations", []),
        "retrieved": item.get("retrieved", []),
        "verifier_report": item.get("verifier_report", {}),
        "timings": item.get("timings", {}),
        "error": item.get("error"),
    }


def _retrieved_chunk_dict(chunk) -> dict:
    return {
        "id": chunk.id,
        "document_id": chunk.document_id,
        "page_number": chunk.page_number,
        "modality": chunk.modality,
        "score": chunk.score,
        "citation": chunk.citation,
    }


def _store_result_on_case(item: dict, result: dict) -> None:
    for field in RESULT_FIELDS:
        item.pop(field, None)
    item.update({field: result[field] for field in RESULT_FIELDS})


def _append_markdown_result(out_md: Path, item: dict) -> None:
    with out_md.open("a", encoding="utf-8") as handle:
        handle.write(f"## {item['id']}\n\n")
        handle.write(f"**Question:** {item['question']}\n\n")
        if item.get("error"):
            handle.write(f"**Error:** {item['error']}\n\n")
        else:
            handle.write(f"**Answer:** {item['answer']}\n\n")
        handle.write(f"**Fallback:** {item['is_fallback']}\n\n")
        citations = ", ".join(item["citations"]) if item["citations"] else "None"
        handle.write(f"**Citations:** {citations}\n\n")


if __name__ == "__main__":
    main()
