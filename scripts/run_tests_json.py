from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "service" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from powermind_rag.config import RAGConfig
from powermind_rag.pipeline import MultimodalRAGPipeline


def progress(message: str) -> None:
    print(f"[tests-json] {message}", flush=True)


def _load_questions(tests_path: Path) -> list[str]:
    payload = json.loads(tests_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        questions = payload.get("questions", [])
    elif isinstance(payload, list):
        questions = payload
    else:
        raise ValueError(f"Unsupported tests format in {tests_path}")
    if not isinstance(questions, list) or not questions:
        raise ValueError(f"No questions found in {tests_path}")
    normalized: list[str] = []
    for item in questions:
        if isinstance(item, str) and item.strip():
            normalized.append(item.strip())
    if not normalized:
        raise ValueError(f"No valid questions found in {tests_path}")
    return normalized


def _retrieved_chunk_dict(chunk) -> dict:
    return {
        "id": chunk.id,
        "document_id": chunk.document_id,
        "page_number": chunk.page_number,
        "modality": chunk.modality,
        "score": chunk.score,
        "citation": chunk.citation,
    }


def main() -> int:
    tests_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "service" / "tests.json"
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "service" / "tests_results.json"
    md_output_path = output_path.with_suffix(".md")

    questions = _load_questions(tests_path)
    cfg = RAGConfig.from_env()
    progress(
        f"loading pipeline storage_dir={cfg.storage_dir.resolve()} device={cfg.device} local_only={cfg.local_only}"
    )
    pipeline = MultimodalRAGPipeline(cfg)
    pipeline.load_from_storage()

    results = []
    suite_start = perf_counter()
    for index, question in enumerate(questions, start=1):
        start = perf_counter()
        progress(f"question {index}/{len(questions)} started")
        try:
            answer = pipeline.answer(question)
            elapsed = perf_counter() - start
            progress(
                f"question {index}/{len(questions)} done in {elapsed:.1f}s fallback={answer.is_fallback} citations={len(answer.retrieved)}"
            )
            results.append(
                {
                    "index": index,
                    "question": question,
                    "answer": answer.text,
                    "is_fallback": answer.is_fallback,
                    "citations": [chunk.citation for chunk in answer.retrieved],
                    "retrieved": [_retrieved_chunk_dict(chunk) for chunk in answer.retrieved],
                    "verifier_report": answer.verifier_report,
                    "timings": answer.timings,
                    "elapsed_seconds": elapsed,
                    "error": None,
                }
            )
        except Exception as exc:  # noqa: BLE001
            elapsed = perf_counter() - start
            progress(f"question {index}/{len(questions)} failed in {elapsed:.1f}s error={exc}")
            results.append(
                {
                    "index": index,
                    "question": question,
                    "answer": "",
                    "is_fallback": True,
                    "citations": [],
                    "retrieved": [],
                    "verifier_report": {},
                    "timings": {},
                    "elapsed_seconds": elapsed,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    payload = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "tests_path": str(tests_path),
        "storage_dir": str(cfg.storage_dir.resolve()),
        "total_questions": len(questions),
        "total_elapsed_seconds": perf_counter() - suite_start,
        "results": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# tests.json results",
        "",
        f"- Questions: `{len(questions)}`",
        f"- Tests path: `{tests_path}`",
        f"- Storage dir: `{cfg.storage_dir.resolve()}`",
        "",
    ]
    for item in results:
        lines.extend(
            [
                f"## {item['index']}. {item['question']}",
                "",
                item.get("answer") or f"ERROR: {item.get('error', '')}",
                "",
                f"- Fallback: `{item.get('is_fallback')}`",
                f"- Citations: {', '.join(item['citations']) if item['citations'] else 'None'}",
                f"- Elapsed: `{item.get('elapsed_seconds'):.1f}s`",
                "",
            ]
        )
    md_output_path.write_text("\n".join(lines), encoding="utf-8")

    progress(f"wrote JSON results to {output_path}")
    progress(f"wrote Markdown results to {md_output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())