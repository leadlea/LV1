"""PBT-exploration: LV3 _parse_questions bug condition exploration test.

Feature: lv3-generate-timeout-fix
Property: Fault Condition - stop_reason=max_tokens の切り詰められたレスポンスが
チェックなしでパースに渡される

This test demonstrates that the ORIGINAL (unfixed) _parse_questions would pass
truncated JSON responses with stop_reason=max_tokens directly to json.loads
without checking stop_reason, while the FIXED version detects the truncation
and logs a warning.

**Validates: Requirements 1.4, 2.4**
"""

import json
import logging
import logging.handlers

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from backend.handlers.lv3_generate_handler import (
    _parse_questions,
    STEP_TYPE_MAP,
    EXPECTED_NUM_QUESTIONS,
)
from backend.lib.bedrock_client import strip_code_fence


# ---------------------------------------------------------------------------
# Simulated ORIGINAL (unfixed) _parse_questions — no stop_reason check
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)


def _parse_questions_original(result: dict) -> list[dict]:
    """Replica of the ORIGINAL _parse_questions before the bugfix.

    Key difference from the fixed version:
    - No stop_reason check — truncated responses with stop_reason=max_tokens
      are passed directly to json.loads without any early detection.
    """
    # NOTE: No stop_reason check here — this is the bug
    text = result.get("content", [{}])[0].get("text", "")
    text = strip_code_fence(text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse Bedrock response as JSON: %s", text[:200])
        raise ValueError("Bedrock response is not valid JSON")

    questions = data.get("questions")
    if not isinstance(questions, list) or len(questions) != EXPECTED_NUM_QUESTIONS:
        raise ValueError(
            f"Response must contain exactly {EXPECTED_NUM_QUESTIONS} questions, "
            f"got {len(questions) if isinstance(questions, list) else 'none'}"
        )

    validated = []
    for i, q in enumerate(questions):
        step = q.get("step")
        q_type = q.get("type")
        prompt = q.get("prompt")
        context = q.get("context")

        expected_step = i + 1
        if not isinstance(step, int) or step != expected_step:
            raise ValueError(f"Question {i}: step must be {expected_step}, got {step}")

        expected_type = STEP_TYPE_MAP[expected_step]
        if q_type != expected_type:
            raise ValueError(
                f"Question {i}: step {expected_step} must be type "
                f"'{expected_type}', got '{q_type}'"
            )

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"Question {i}: prompt must be a non-empty string")

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
# Hypothesis strategies
# ---------------------------------------------------------------------------

def _valid_lv3_question(step: int) -> dict:
    """Build a valid LV3 question dict for a given step."""
    return {
        "step": step,
        "type": STEP_TYPE_MAP[step],
        "prompt": f"テスト設問 ステップ{step}",
        "options": None,
        "context": f"テストコンテキスト ステップ{step}の説明文",
    }


def _full_valid_json() -> str:
    """Build a complete valid 5-question JSON string."""
    questions = [_valid_lv3_question(s) for s in range(1, 6)]
    return json.dumps({"questions": questions}, ensure_ascii=False)


@st.composite
def truncated_json_response(draw):
    """Generate a Bedrock response with stop_reason=max_tokens and truncated JSON.

    Simulates what happens when max_tokens is insufficient: the JSON output
    is cut off at a random position, producing invalid JSON.
    """
    full_json = _full_valid_json()

    # Truncate at a random position — ensure we cut off enough to break JSON
    # At minimum keep some content, at maximum cut at least 10 chars from end
    min_cut = max(10, len(full_json) // 4)
    max_keep = len(full_json) - 10
    cut_pos = draw(st.integers(min_value=min_cut, max_value=max_keep))
    truncated = full_json[:cut_pos]

    return {
        "content": [{"text": truncated}],
        "stop_reason": "max_tokens",
    }


@st.composite
def valid_lv3_response(draw):
    """Generate a valid complete LV3 Bedrock response with stop_reason=end_turn."""
    prompts = [
        draw(st.text(min_size=1, max_size=100).filter(lambda s: s.strip()))
        for _ in range(EXPECTED_NUM_QUESTIONS)
    ]
    contexts = [
        draw(st.text(min_size=1, max_size=200).filter(lambda s: s.strip()))
        for _ in range(EXPECTED_NUM_QUESTIONS)
    ]

    questions = []
    for i in range(EXPECTED_NUM_QUESTIONS):
        step = i + 1
        questions.append({
            "step": step,
            "type": STEP_TYPE_MAP[step],
            "prompt": prompts[i],
            "options": None,
            "context": contexts[i],
        })

    return {
        "content": [{"text": json.dumps({"questions": questions}, ensure_ascii=False)}],
        "stop_reason": "end_turn",
    }


# ---------------------------------------------------------------------------
# Exploration tests
# ---------------------------------------------------------------------------

@given(response=truncated_json_response())
@settings(max_examples=200)
def test_original_parse_no_stop_reason_check_on_truncated(response):
    """Exploration: The ORIGINAL _parse_questions has no stop_reason check,
    so truncated responses with stop_reason=max_tokens are passed directly
    to json.loads, resulting in ValueError (from JSONDecodeError or validation).

    The original code never inspects stop_reason — it blindly attempts to parse
    whatever text is in the response, even when Bedrock signals truncation.

    **Validates: Requirements 1.4**
    """
    # The truncated JSON should cause the original parser to raise ValueError
    # because it has no stop_reason check and the JSON is incomplete
    with pytest.raises(ValueError):
        _parse_questions_original(response)


@given(response=truncated_json_response())
@settings(max_examples=200)
def test_fixed_parse_detects_stop_reason_max_tokens(response):
    """Exploration: The FIXED _parse_questions checks stop_reason=max_tokens
    and logs a warning before attempting to parse truncated JSON.

    Even though the parse will still fail (JSON is truncated), the fix ensures
    the truncation is detected and logged, providing clear diagnostics.

    **Validates: Requirements 2.4**
    """
    log_handler = logging.handlers.MemoryHandler(capacity=100)
    test_logger = logging.getLogger("backend.handlers.lv3_generate_handler")
    test_logger.addHandler(log_handler)
    test_logger.setLevel(logging.WARNING)

    try:
        # The fixed version will still raise ValueError on truncated JSON,
        # but it first logs a warning about the truncation
        with pytest.raises(ValueError):
            _parse_questions(response)

        # Verify the fix: stop_reason=max_tokens was detected and logged
        warning_logged = any(
            "truncated due to max_tokens" in record.message
            for record in log_handler.buffer
        )
        assert warning_logged, (
            "Fixed _parse_questions should log a warning when stop_reason is max_tokens"
        )
    finally:
        test_logger.removeHandler(log_handler)
        log_handler.close()


@given(response=valid_lv3_response())
@settings(max_examples=100)
def test_both_versions_agree_on_valid_responses(response):
    """Exploration: Both original and fixed _parse_questions produce identical
    results for valid (non-truncated) responses with stop_reason=end_turn.

    This confirms the fix does not change behavior for normal responses.

    **Validates: Requirements 2.4**
    """
    original_result = _parse_questions_original(response)
    fixed_result = _parse_questions(response)

    assert original_result == fixed_result
