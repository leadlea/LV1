"""Property-based tests for grade_handler.

Feature: ai-levels-lv1-mvp, Property 3: 採点結果の構造的正当性

Validates: Requirements 2.1, 2.3
"""

import json
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.handlers.grade_handler import handler

VALID_TYPES = ["multiple_choice", "free_text", "scenario"]


def _question_strategy():
    """Generate a valid question dict."""
    return st.fixed_dictionaries({
        "step": st.integers(min_value=1, max_value=20),
        "type": st.sampled_from(VALID_TYPES),
        "prompt": st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
    })


def _bedrock_grade_response(passed: bool, score: int) -> dict:
    return {"content": [{"text": json.dumps({"passed": passed, "score": score})}]}


@given(
    session_id=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
    step=st.integers(min_value=1, max_value=20),
    question=_question_strategy(),
    answer=st.text(min_size=1, max_size=300).filter(lambda s: s.strip()),
    passed=st.booleans(),
    score=st.integers(min_value=0, max_value=100),
)
@settings(max_examples=100)
def test_grade_response_structure(session_id, step, question, answer, passed, score):
    """Property 3: 採点結果の構造的正当性

    任意の設問と回答の組み合わせに対して、Graderが返す採点結果は、
    passed（bool型）とscore（0〜100の整数）を含む正しい構造であること。

    **Validates: Requirements 2.1, 2.3**
    """
    event = {
        "body": json.dumps({
            "session_id": session_id,
            "step": step,
            "question": question,
            "answer": answer,
        })
    }

    with (
        patch("backend.handlers.grade_handler.invoke_claude") as mock_invoke,
        patch("backend.handlers.grade_handler.generate_feedback") as mock_review,
    ):
        mock_invoke.return_value = _bedrock_grade_response(passed, score)
        mock_review.return_value = {"feedback": "Good job", "explanation": "Explanation"}
        resp = handler(event, None)

    assert resp["statusCode"] == 200

    body = json.loads(resp["body"])

    # session_id echoed back
    assert body["session_id"] == session_id

    # step echoed back
    assert body["step"] == step

    # passed is a boolean
    assert isinstance(body["passed"], bool)
    assert body["passed"] == passed

    # score is an integer in 0-100
    assert isinstance(body["score"], int)
    assert 0 <= body["score"] <= 100
