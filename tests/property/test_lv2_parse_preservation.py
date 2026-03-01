"""PBT-preservation: 修正後の _parse_questions が正常な4問JSONに対して修正前と同一の結果を返すことを検証。

Feature: lv2-start-failure-fix
Property: Preservation - 既存エンドポイントの動作不変

正常な4問JSON（全フィールド有効値）を生成し、修正前の厳格な _parse_questions と
修正後の寛容な _parse_questions が同一の結果を返すことを検証する。
これにより、修正が既に正常に動作していた入力の振る舞いを変えないことを証明する。

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
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
# Simulated ORIGINAL (strict) _parse_questions — replicates the OLD behavior
# ---------------------------------------------------------------------------

def _parse_questions_original(result: dict) -> list[dict]:
    """Replica of the ORIGINAL strict _parse_questions before the bugfix.

    Key differences from the fixed version:
    - context = q.get("context") with strict check:
      if not isinstance(context, str) or not context.strip(): raise ValueError
    - q_type = q.get("type") with exact match (no strip/lower normalization)
    - No stop_reason check
    """
    text = result.get("content", [{}])[0].get("text", "")

    data = json.loads(text)

    questions = data.get("questions")
    if not isinstance(questions, list) or len(questions) != EXPECTED_NUM_QUESTIONS:
        raise ValueError(
            f"Response must contain exactly {EXPECTED_NUM_QUESTIONS} questions"
        )

    validated = []
    for i, q in enumerate(questions):
        step = q.get("step")
        q_type = q.get("type")  # NO .strip().lower() — original strict behavior
        prompt = q.get("prompt")
        context = q.get("context")  # strict: must be non-empty string

        expected_step = i + 1
        if not isinstance(step, int) or step != expected_step:
            raise ValueError(f"Question {i}: step must be {expected_step}, got {step}")

        expected_type = STEP_TYPE_MAP[expected_step]
        if q_type != expected_type:  # exact match only
            raise ValueError(
                f"Question {i}: step {expected_step} must be type "
                f"'{expected_type}', got '{q_type}'"
            )

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"Question {i}: prompt must be a non-empty string")

        # Original strict check: context must be a non-empty string
        if not isinstance(context, str) or not context.strip():
            raise ValueError(f"Question {i}: context must be a non-empty string")

        validated.append({
            "step": step,
            "type": q_type,
            "prompt": prompt,
            "options": None,
            "context": context,
        })

    return validated


# ---------------------------------------------------------------------------
# Hypothesis strategies — NORMAL/VALID inputs only
# ---------------------------------------------------------------------------

def _valid_nonempty_string() -> st.SearchStrategy[str]:
    """Generate non-empty valid strings (NOT null, NOT empty)."""
    return st.text(min_size=1, max_size=300).filter(lambda s: s.strip())


def _lv2_valid_question(step: int) -> st.SearchStrategy[dict]:
    """Generate a single LV2 question with ALL valid fields.

    - context: non-empty valid string (NOT null, NOT empty)
    - type: exact lowercase match ("scenario" or "free_text")
    - prompt: non-empty string
    - step: correct 1-4 sequence
    - options: always null
    """
    return st.fixed_dictionaries({
        "step": st.just(step),
        "type": st.just(STEP_TYPE_MAP[step]),  # exact lowercase match
        "prompt": _valid_nonempty_string(),
        "options": st.just(None),
        "context": _valid_nonempty_string(),
    })


def _lv2_valid_bedrock_response() -> st.SearchStrategy[dict]:
    """Generate a full 4-question LV2 Bedrock response with all valid fields."""
    return st.tuples(
        _lv2_valid_question(1),
        _lv2_valid_question(2),
        _lv2_valid_question(3),
        _lv2_valid_question(4),
    ).map(lambda qs: {
        "content": [{"text": json.dumps({"questions": list(qs)}, ensure_ascii=False)}],
        "stop_reason": "end_turn",
    })


# ---------------------------------------------------------------------------
# Property-based test
# ---------------------------------------------------------------------------

@given(response=_lv2_valid_bedrock_response())
@settings(max_examples=200)
def test_fixed_parse_preserves_original_behavior_for_valid_inputs(response):
    """修正後の _parse_questions は、正常な4問JSON（全フィールド有効値）に対して
    修正前の _parse_questions_original と同一の結果を返す。

    これにより、修正が既に正常に動作していた入力の振る舞いを変えないことを証明する。

    **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
    """
    # Both versions should succeed on valid inputs
    original_result = _parse_questions_original(response)
    fixed_result = _parse_questions(response)

    # Results must be identical
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
