"""PBT-fix: 修正後の _parse_questions が有効なLV2ケーススタディJSONを正しくパースすることを検証。

Feature: lv2-start-failure-fix
Property: Fault Condition - LV2ケーススタディ生成の完全なJSON返却

修正後の _parse_questions に対して、contextがnull/空文字列/有効文字列、
typeの大文字小文字バリエーションを含むランダムなLV2レスポンスを生成し、
正しくパースされることを検証する。

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**
"""

import json

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.handlers.lv2_generate_handler import (
    _parse_questions,
    STEP_TYPE_MAP,
    EXPECTED_NUM_QUESTIONS,
)


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

def _type_case_variations(step: int) -> st.SearchStrategy[str]:
    """Generate type values with case/whitespace variations for a given step."""
    base = STEP_TYPE_MAP[step]  # "scenario" or "free_text"
    variants = [
        base,                    # "scenario" / "free_text"
        base.capitalize(),       # "Scenario" / "Free_text"
        base.upper(),            # "SCENARIO" / "FREE_TEXT"
        f" {base} ",            # " scenario " / " free_text "
        base.title(),            # "Scenario" / "Free_Text"
        f"  {base.upper()}  ",  # "  SCENARIO  " / "  FREE_TEXT  "
    ]
    return st.sampled_from(variants)


def _context_strategy() -> st.SearchStrategy:
    """Generate context values: null, empty string, or valid non-empty strings."""
    return st.one_of(
        st.none(),
        st.just(""),
        st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
    )


def _lv2_question(step: int) -> st.SearchStrategy[dict]:
    """Generate a single LV2 question dict for a given step."""
    return st.fixed_dictionaries({
        "step": st.just(step),
        "type": _type_case_variations(step),
        "prompt": st.text(min_size=1, max_size=300).filter(lambda s: s.strip()),
        "options": st.just(None),
        "context": _context_strategy(),
    })


def _lv2_bedrock_response() -> st.SearchStrategy[dict]:
    """Generate a full 4-question LV2 Bedrock response dict."""
    return st.tuples(
        _lv2_question(1),
        _lv2_question(2),
        _lv2_question(3),
        _lv2_question(4),
    ).map(lambda qs: {
        "content": [{"text": json.dumps({"questions": list(qs)}, ensure_ascii=False)}],
        "stop_reason": "end_turn",
    })


# ---------------------------------------------------------------------------
# Property-based test
# ---------------------------------------------------------------------------

@given(response=_lv2_bedrock_response())
@settings(max_examples=200)
def test_fixed_parse_questions_handles_all_valid_variations(response):
    """修正後の _parse_questions はcontextがnull/空文字列/有効文字列、
    typeの大文字小文字バリエーションを含む有効なLV2レスポンスを
    正しくパースし、正規化された結果を返す。

    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    """
    # Extract original input questions for later comparison
    original_questions = json.loads(response["content"][0]["text"])["questions"]

    # _parse_questions should NOT raise ValueError
    result = _parse_questions(response)

    # Result is a list of exactly 4 dicts
    assert isinstance(result, list)
    assert len(result) == EXPECTED_NUM_QUESTIONS

    for i, q in enumerate(result):
        step = i + 1

        # Each question has correct step (1-4)
        assert q["step"] == step

        # Each type is normalized to lowercase ("scenario" or "free_text")
        assert q["type"] == STEP_TYPE_MAP[step]

        # Each prompt is preserved as-is
        assert q["prompt"] == original_questions[i]["prompt"]

        # Context is a string (null converted to "")
        assert isinstance(q["context"], str)
        orig_ctx = original_questions[i].get("context")
        if orig_ctx is None:
            assert q["context"] == ""
        else:
            assert q["context"] == orig_ctx

        # Options is None
        assert q["options"] is None
