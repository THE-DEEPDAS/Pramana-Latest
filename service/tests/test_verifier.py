from powermind_rag.verifier import LettuceClaimVerifier


def test_empty_unsupported_spans_do_not_fail():
    assert not LettuceClaimVerifier.has_unsupported_content(
        {"unsupported_spans": [], "is_supported": True}
    )


def test_unsupported_spans_fail():
    assert LettuceClaimVerifier.has_unsupported_content(
        {"unsupported_spans": [{"text": "123"}], "is_supported": False}
    )
