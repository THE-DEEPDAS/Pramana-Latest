from powermind_rag.relevance import _normalize_api_keys


def test_normalize_api_keys_keeps_both_gemini_keys_without_duplicates():
    assert _normalize_api_keys([" first ", "second", "first", None, ""]) == [
        "first",
        "second",
    ]
