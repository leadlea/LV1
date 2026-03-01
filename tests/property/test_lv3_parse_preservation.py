"""PBT-preservation: 修正後の _parse_questions が正常な5問JSONに対して修正前と同一の結果を返すことを検証。

Feature: lv3-generate-timeout-fix
Property: Preservation - 既存エンドポイントの動作不変

正常な5問JSON（stop_reason=end_turn、全フィールド有効値）を生成し、
修正前の _parse_questions_original と修正後の _parse_questions が
同一の結果を返すことを検証する。
これにより、stop_reason チェック追加が正常入力の振る舞いを変えないことを証明する。

**Validates: Requirements 3.3**
"""

import json

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.handlers.lv3_generate_handler import (
    _parse_questions,
    STEP_TYPE_MAP,
    EXPECTED_NUM_QUESTIONS,
)
from tests.property.test_lv3_parse_exploration import _parse_questions_original


# ---------------------------------------------------------------------------
# Hypothesis strategies — NORMAL/VALID inputs only
# ---------------------------------------------------------------------------

def _valid_nonempty_string() -> st.SearchStrategy[str]:
    """Generate non-empty valid strings."""
    return st.text(min_size=1, max_size=300).filter(lambda s: s.strip())


def _lv3_valid_question(step: int) -> st.SearchStrategy[dict]:
    """Generate a single valid LV3 question dict for a given step."""
    return st.fixed_dictionaries({
        "step": st.just(step),
        "type": st.just(STEP_TYPE_MAP[step]),
        "prompt": _valid_nonempty_string(),
        "options": st.just(None),
        "context": _valid_nonempty_string(),
    })


@st.composite
def valid_lv3_bedrock_response(draw):
    """Generate a full 5-question LV3 Bedrock response with stop_reason=end_turn."""
    questions = [draw(_lv3_valid_question(step)) for step in range(1, EXPECTED_NUM_QUESTIONS + 1)]
    return {
        "content": [{"text": json.dumps({"questions": questions}, ensure_ascii=False)}],
        "stop_reason": "end_turn",
    }


# ---------------------------------------------------------------------------
# Property-based test
# ---------------------------------------------------------------------------

@given(response=valid_lv3_bedrock_response())
@settings(max_examples=200)
def test_fixed_parse_preserves_original_behavior_for_valid_inputs(response):
    """修正後の _parse_questions は、正常な5問JSON（stop_reason=end_turn）に対して
    修正前の _parse_questions_original と同一の結果を返す。

    修正前コードには stop_reason チェックがなく、修正後コードには stop_reason チェックが
    追加されているが、stop_reason=end_turn の正常レスポンスに対しては両者とも
    同一のパース結果を返すことを証明する。

    **Validates: Requirements 3.3**
    """
    original_result = _parse_questions_original(response)
    fixed_result = _parse_questions(response)

    assert original_result == fixed_result, (
        f"Results differ!\n"
        f"Original: {original_result}\n"
        f"Fixed:    {fixed_result}"
    )

    # Additional structural validation
    assert len(fixed_result) == EXPECTED_NUM_QUESTIONS
    for i, q in enumerate(fixed_result):
        assert q["step"] == i + 1
        assert q["type"] == STEP_TYPE_MAP[i + 1]
        assert isinstance(q["prompt"], str) and q["prompt"].strip()
        assert isinstance(q["context"], str) and q["context"].strip()
        assert q["options"] is None
