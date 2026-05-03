from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "service" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from powermind_rag.config import RAGConfig
from powermind_rag.pipeline import MultimodalRAGPipeline


def main() -> None:
    batch_path = ROOT / "service" / "test_cases.json"
    out_dir = ROOT / "service" / "outputs"
    out_md = out_dir / "qa_results.md"
    out_json = out_dir / "qa_results.json"

    batch_data = json.loads(batch_path.read_text(encoding="utf-8"))
    questions = []
    max_per_category = 3
    for category, items in batch_data.items():
        if not isinstance(items, list):
            continue
        for item in items[:max_per_category]:
            if not isinstance(item, dict) or "question" not in item:
                continue
            questions.append({
                **item,
                "category_group": category,
                "source": item.get("source", category),
                "category": item.get("category", category.title()),
                "type": item.get("type", "Unknown"),
            })

    pipeline = MultimodalRAGPipeline(RAGConfig.from_env())
    pipeline.load_from_storage()

    out_dir.mkdir(parents=True, exist_ok=True)
    out_md.write_text("# PowerMind RAG Question Results\n\n", encoding="utf-8")
    out_json.write_text("[]", encoding="utf-8")

    results = []
    for idx, item in enumerate(questions, 1):
        print(f"Processing {idx}/{len(questions)}: {item['category_group']}-{item['id']} ...", flush=True)
        answer = pipeline.answer(item["question"])
        result = {
            "id": f'{item["category_group"]}-{item["id"]}',
            "question": item["question"],
            "source": item["source"],
            "category": item["category"],
            "type": item["type"],
            "category_group": item["category_group"],
            "answer": answer.text,
            "is_fallback": answer.is_fallback,
            "citations": [chunk.citation for chunk in answer.retrieved],
            "retrieved": [
                {
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "page_number": chunk.page_number,
                    "modality": chunk.modality,
                    "score": chunk.score,
                    "citation": chunk.citation,
                }
                for chunk in answer.retrieved
            ],
            "verifier_report": answer.verifier_report,
            "timings": answer.timings,
        }
        results.append(result)
        print(f"Answered {result['id']}: {result['answer']}", flush=True)
        _append_markdown_result(out_md, result)
        out_json.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"Wrote {out_md}", flush=True)
    print(f"Wrote {out_json}", flush=True)


def _append_markdown_result(out_md: Path, item: dict) -> None:
    with out_md.open("a", encoding="utf-8") as handle:
        handle.write(f"## {item['id']}\n\n")
        handle.write(f"**Question:** {item['question']}\n\n")
        handle.write(f"**Answer:** {item['answer']}\n\n")
        handle.write(f"**Fallback:** {item['is_fallback']}\n\n")
        citations = ", ".join(item["citations"]) if item["citations"] else "None"
        handle.write(f"**Citations:** {citations}\n\n")


if __name__ == "__main__":
    main()