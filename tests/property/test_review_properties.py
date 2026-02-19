"""Property-based tests for reviewer.

Feature: ai-levels-lv1-mvp, Property 4: レビュー結果の構造的正当性

Validates: Requirements 3.1
"""

import json
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.lib.reviewer import generate_feedback

VALID_TYPES = ["multiple_choice", "free_text", "scenario"]


def _question_strategy():
    """Generate a valid question dict."""
    return st.fixed_dictionaries({
        "step": st.integers(min_value=1, max_value=20),
        "type": st.sampled_from(VALID_TYPES),
        "prompt": st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
    })


def _bedrock_review_response(feedback: str, explanation: str) -> dict:
    return {
        "content": [{"text": json.dumps({"feedback": feedback, "explanation": explanation}, ensure_ascii=False)}]
    }


@given(
    question=_question_strategy(),
    answer=st.text(min_size=1, max_size=300).filter(lambda s: s.strip()),
    passed=st.booleans(),
    score=st.integers(min_value=0, max_value=100),
    feedback=st.text(min_size=1, max_size=300).filter(lambda s: s.strip()),
    explanation=st.text(min_size=1, max_size=300).filter(lambda s: s.strip()),
)
@settings(max_examples=100)
def test_review_response_structure(question, answer, passed, score, feedback, explanation):
    """Property 4: レビュー結果の構造的正当性

    任意の採点結果に対して、Reviewerが返すレビュー結果は、
    feedback（空でない文字列）とexplanation（空でない文字列）の両フィールドを含むこと。

    **Validates: Requirements 3.1**
    """
    grade_result = {"passed": passed, "score": score}

    with patch("backend.lib.reviewer.invoke_claude") as mock_invoke:
        mock_invoke.return_value = _bedrock_review_response(feedback, explanation)
        result = generate_feedback(question, answer, grade_result)

    # feedback is a non-empty string
    assert isinstance(result["feedback"], str)
    assert result["feedback"].strip() != ""

    # explanation is a non-empty string
    assert isinstance(result["explanation"], str)
    assert result["explanation"].strip() != ""
