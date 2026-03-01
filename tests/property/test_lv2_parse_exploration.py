"""PBT-exploration: LV2 _parse_questions bug condition exploration test.

Feature: lv2-start-failure-fix
Property: Fault Condition - contextがnullやtypeの大文字小文字差異でValueErrorが発生する

This test demonstrates that the ORIGINAL (unfixed) _parse_questions would raise
ValueError on LV2 responses with null context or type case variations, while the
FIXED version handles them correctly.

**Validates: Requirements 1.4, 2.4**
"""

import json

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from backend.handlers.lv2_generate_handler import (
    _parse_questions,
    STEP_TYPE_MAP,
    EXPECTED_NUM_QUESTIONS,
)


# ---------------------------------------------------------------------------
# Simulated ORIGINAL (strict) _parse_questions — replicates the old buggy code
# ---------------------------------------------------------------------------

def _parse_questions_original(result: dict) -> list[dict]:
    """Replica of the ORIGINAL strict _parse_questions before the bugfix.

    Key differences from the fixed version:
    - context must be a non-empty string (null/None raises ValueError)
    - type must exactly match STEP_TYPE_MAP values (no strip/lower normalization)
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
        context = q.get("context")

        expected_step = i + 1
        if not isinstance(step, int) or step != expected_step:
            raise ValueError(f"Question {i}: step must be {expected_step}, got {step}")

        expected_type = STEP_TYPE_MAP[expected_step]
        if q_type != expected_type:  # exact match only — original strict behavior
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
# Hypothesis strategies
# ---------------------------------------------------------------------------

def _type_case_variation(step: int) -> st.SearchStrategy[str]:
    """Generate type values with case variations for a given step."""
    base = STEP_TYPE_MAP[step]  # "scenario" or "free_text"
    variants = [
        base,                # exact match (original would accept)
        base.upper(),        # "SCENARIO" / "FREE_TEXT"
        base.capitalize(),   # "Scenario" / "Free_text"
        base.title(),        # "Scenario" / "Free_Text"
        f" {base} ",         # padded with spaces
        f"  {base.upper()}  ",
    ]
    return st.sampled_from(variants)


def _context_strategy() -> st.SearchStrategy:
    """Generate context values including null and valid strings."""
    return st.one_of(
        st.none(),                                          # null context (bug trigger)
        st.just(""),                                        # empty string
        st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),  # valid
    )


def _lv2_question_strategy(step: int, use_case_variation: bool = True):
    """Generate a single LV2 question dict for a given step."""
    type_st = _type_case_variation(step) if use_case_variation else st.just(STEP_TYPE_MAP[step])
    return st.fixed_dictionaries({
        "step": st.just(step),
        "type": type_st,
        "prompt": st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
        "options": st.just(None),
        "context": _context_strategy(),
    })


def _lv2_response_strategy(use_case_variation: bool = True):
    """Generate a full 4-question LV2 Bedrock response."""
    return st.tuples(
        _lv2_question_strategy(1, use_case_variation),
        _lv2_question_strategy(2, use_case_variation),
        _lv2_question_strategy(3, use_case_variation),
        _lv2_question_strategy(4, use_case_variation),
    ).map(lambda qs: {
        "content": [{"text": json.dumps({"questions": list(qs)}, ensure_ascii=False)}],
        "stop_reason": "end_turn",
    })


def _has_bug_trigger(questions: list[dict]) -> bool:
    """Check if any question has a null/empty context or non-exact type match."""
    for i, q in enumerate(questions):
        expected_type = STEP_TYPE_MAP[i + 1]
        # Type case variation (not exact lowercase match)
        if q.get("type") != expected_type:
            return True
        # Null or empty context
        ctx = q.get("context")
        if ctx is None or (isinstance(ctx, str) and not ctx.strip()):
            return True
    return False


# ---------------------------------------------------------------------------
# Exploration tests
# ---------------------------------------------------------------------------

@given(response=_lv2_response_strategy(use_case_variation=True))
@settings(max_examples=200)
def test_original_parse_raises_on_bug_conditions(response):
    """Exploration: The ORIGINAL strict _parse_questions raises ValueError
    on inputs with null context or type case variations.

    This confirms the bug existed in the original code.

    **Validates: Requirements 1.4**
    """
    text = response["content"][0]["text"]
    questions = json.loads(text)["questions"]

    # Only test inputs that actually trigger the bug condition
    assume(_has_bug_trigger(questions))

    with pytest.raises(ValueError):
        _parse_questions_original(response)


@given(response=_lv2_response_strategy(use_case_variation=True))
@settings(max_examples=200)
def test_fixed_parse_handles_bug_conditions(response):
    """Exploration: The FIXED _parse_questions handles null context and
    type case variations without raising ValueError.

    This confirms the fix resolves the bug.

    **Validates: Requirements 2.4**
    """
    text = response["content"][0]["text"]
    questions = json.loads(text)["questions"]

    # Only test inputs that would have triggered the bug
    assume(_has_bug_trigger(questions))

    # Fixed version should NOT raise
    result = _parse_questions(response)

    # Validate the result structure
    assert isinstance(result, list)
    assert len(result) == EXPECTED_NUM_QUESTIONS

    for i, q in enumerate(result):
        assert q["step"] == i + 1
        assert q["type"] == STEP_TYPE_MAP[i + 1]  # normalized to lowercase
        assert isinstance(q["prompt"], str) and q["prompt"].strip()
        assert isinstance(q["context"], str)  # null converted to ""
        assert q["options"] is None
