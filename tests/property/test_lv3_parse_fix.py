"""PBT-fix: 修正後の _parse_questions が有効なLV3シナリオJSONを正しくパースすることを検証。

Feature: lv3-generate-timeout-fix
Property: Fault Condition - LV3シナリオ生成の完全なJSON返却

ランダムな有効LV3シナリオJSON（5問、各フィールド有効値）を生成し、
修正後の _parse_questions が正しくパースされることを検証する。

**Validates: Requirements 2.1, 2.3, 2.4**
"""

import json

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.handlers.lv3_generate_handler import (
    _parse_questions,
    STEP_TYPE_MAP,
    EXPECTED_NUM_QUESTIONS,
)


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------


def _lv3_question(step: int) -> st.SearchStrategy[dict]:
    """Generate a single valid LV3 question dict for a given step."""
    return st.fixed_dictionaries({
        "step": st.just(step),
        "type": st.just(STEP_TYPE_MAP[step]),
        "prompt": st.text(min_size=1, max_size=300).filter(lambda s: s.strip()),
        "options": st.just(None),
        "context": st.text(min_size=1, max_size=300).filter(lambda s: s.strip()),
    })


@st.composite
def valid_lv3_bedrock_response(draw):
    """Generate a full 5-question LV3 Bedrock response with stop_reason=end_turn."""
    questions = [draw(_lv3_question(step)) for step in range(1, EXPECTED_NUM_QUESTIONS + 1)]
    return {
        "content": [{"text": json.dumps({"questions": questions}, ensure_ascii=False)}],
        "stop_reason": "end_turn",
    }


# ---------------------------------------------------------------------------
# Property-based test
# ---------------------------------------------------------------------------


@given(response=valid_lv3_bedrock_response())
@settings(max_examples=200)
def test_fixed_parse_questions_correctly_parses_valid_lv3_scenarios(response):
    """修正後の _parse_questions はランダムな有効LV3シナリオJSON（5問）を
    正しくパースし、各フィールドが期待通りの値を持つことを検証する。

    **Validates: Requirements 2.1, 2.3, 2.4**
    """
    original_questions = json.loads(response["content"][0]["text"])["questions"]

    result = _parse_questions(response)

    assert isinstance(result, list)
    assert len(result) == EXPECTED_NUM_QUESTIONS

    for i, q in enumerate(result):
        step = i + 1

        assert q["step"] == step
        assert q["type"] == STEP_TYPE_MAP[step]
        assert q["prompt"] == original_questions[i]["prompt"]
        assert q["context"] == original_questions[i]["context"]
        assert q["options"] is None
