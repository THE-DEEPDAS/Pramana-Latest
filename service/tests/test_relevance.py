from powermind_rag.relevance import (
    _extract_json_object,
    _extract_score_pairs,
    _normalize_api_keys,
    _parse_scores_payload,
)


def test_normalize_api_keys_keeps_both_gemini_keys_without_duplicates():
    assert _normalize_api_keys([" first ", "second", "first", None, ""]) == [
        "first",
        "second",
    ]


def test_extract_json_object_handles_prefaced_fenced_json():
    text = 'Here is the JSON requested:\n```json\n{"scores": {"0": 1.0}}\n```'
    assert _extract_json_object(text) == '{"scores": {"0": 1.0}}'


def test_parse_scores_payload_repairs_unquoted_numeric_keys():
    assert _parse_scores_payload('{"scores": {0: 1.0, 1: 0.25,}}') == {
        "scores": {"0": 1.0, "1": 0.25}
    }


def test_parse_scores_payload_repairs_missing_commas_between_scores():
    assert _parse_scores_payload('{"scores": {"0": 1.0 "1": 0.25}}') == {
        "scores": {"0": 1.0, "1": 0.25}
    }


def test_extract_score_pairs_from_json_like_text():
    assert _extract_score_pairs('scores: {0: 1.0, "1": 0.25}') == {
        "0": 1.0,
        "1": 0.25,
    }
