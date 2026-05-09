from __future__ import annotations

from app.rag_v2.graph import (
    _apply_page_fallback_answer,
)


def test_page_fallback_keeps_original_answer_when_source_pdf_missing() -> None:
    answer = "The lane-km construction volume in Q2-26 was 456.1."
    page_report = {
        "answer": "Not found in the Documents",
        "found": False,
        "checked_pages": [
            {"page_number": 1, "status": "source_pdf_not_found"},
            {"page_number": 14, "status": "source_pdf_not_found"},
        ],
    }

    assert _apply_page_fallback_answer(answer, page_report) == answer


def test_page_fallback_replaces_answer_when_page_search_finds_one() -> None:
    answer = "Not found in the Documents"
    page_report = {
        "answer": "456.1 [p19]",
        "found": True,
        "checked_pages": [{"page_number": 19, "status": "checked", "answer": "456.1 [p19]"}],
    }

    assert _apply_page_fallback_answer(answer, page_report) == "456.1 [p19]"


