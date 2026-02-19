"""Property-based tests for DB non-write during mid-session.

Feature: ai-levels-lv1-mvp, Property 6: 途中セッションでのDB非書き込み

Validates: Requirements 5.2
"""

import json
from unittest.mock import patch, MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.handlers.generate_handler import handler as generate_handler
from backend.handlers.grade_handler import handler as grade_handler

VALID_TYPES = ["multiple_choice", "free_text", "scenario"]


def _question_strategy():
    """Generate a valid question dict."""
    return st.fixed_dictionaries({
        "step": st.integers(min_value=1, max_value=20),
        "type": st.sampled_from(VALID_TYPES),
        "prompt": st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
    })


def _bedrock_generate_response(questions):
    """Build a mock Bedrock response for generate_handler."""
    return {
        "content": [{"text": json.dumps({"questions": questions}, ensure_ascii=False)}]
    }


def _bedrock_grade_response(passed, score):
    """Build a mock Bedrock response for grade_handler."""
    return {"content": [{"text": json.dumps({"passed": passed, "score": score})}]}


@given(
    session_id=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
    questions=st.lists(_question_strategy(), min_size=1, max_size=6),
)
@settings(max_examples=100)
def test_generate_handler_no_db_write(session_id, questions):
    """Property 6 (generate): 途中セッションでのDB非書き込み

    任意のgenerate_handlerへのリクエストに対して、
    DynamoDBへの書き込み操作が発生しないこと。

    **Validates: Requirements 5.2**
    """
    event = {"body": json.dumps({"session_id": session_id})}

    mock_boto3 = MagicMock()

    with (
        patch("backend.handlers.generate_handler.invoke_claude") as mock_invoke,
        patch("backend.handlers.generate_handler.boto3", mock_boto3, create=True),
        patch("boto3.resource", mock_boto3.resource),
        patch("boto3.client", mock_boto3.client),
    ):
        mock_invoke.return_value = _bedrock_generate_response(questions)
        resp = generate_handler(event, None)

    assert resp["statusCode"] == 200

    # Verify no DynamoDB resource or client was created
    for call in mock_boto3.resource.call_args_list:
        assert call[0][0] != "dynamodb", "generate_handler must not access DynamoDB"
    for call in mock_boto3.client.call_args_list:
        assert call[0][0] != "dynamodb", "generate_handler must not access DynamoDB"


@given(
    session_id=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
    step=st.integers(min_value=1, max_value=20),
    question=_question_strategy(),
    answer=st.text(min_size=1, max_size=300).filter(lambda s: s.strip()),
    passed=st.booleans(),
    score=st.integers(min_value=0, max_value=100),
)
@settings(max_examples=100)
def test_grade_handler_no_db_write(session_id, step, question, answer, passed, score):
    """Property 6 (grade): 途中セッションでのDB非書き込み

    任意のgrade_handlerへのリクエストに対して、
    DynamoDBへの書き込み操作が発生しないこと。

    **Validates: Requirements 5.2**
    """
    event = {
        "body": json.dumps({
            "session_id": session_id,
            "step": step,
            "question": question,
            "answer": answer,
        })
    }

    mock_boto3 = MagicMock()

    with (
        patch("backend.handlers.grade_handler.invoke_claude") as mock_invoke,
        patch("backend.handlers.grade_handler.generate_feedback") as mock_review,
        patch("backend.handlers.grade_handler.boto3", mock_boto3, create=True),
        patch("boto3.resource", mock_boto3.resource),
        patch("boto3.client", mock_boto3.client),
    ):
        mock_invoke.return_value = _bedrock_grade_response(passed, score)
        mock_review.return_value = {"feedback": "Good", "explanation": "Explanation"}
        resp = grade_handler(event, None)

    assert resp["statusCode"] == 200

    # Verify no DynamoDB resource or client was created
    for call in mock_boto3.resource.call_args_list:
        assert call[0][0] != "dynamodb", "grade_handler must not access DynamoDB"
    for call in mock_boto3.client.call_args_list:
        assert call[0][0] != "dynamodb", "grade_handler must not access DynamoDB"
