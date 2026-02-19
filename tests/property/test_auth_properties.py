"""Property-based tests for unauthenticated access to Lv1 endpoints.

Feature: ai-levels-lv1-mvp, Property 8: 認証なしアクセス

Validates: Requirements 7.3
"""

import json
from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.handlers.generate_handler import handler as generate_handler
from backend.handlers.grade_handler import handler as grade_handler
from backend.handlers.complete_handler import handler as complete_handler
from backend.handlers.gate_handler import handler as gate_handler

VALID_TYPES = ["multiple_choice", "free_text", "scenario"]


def _uuid_v4_strategy():
    """Generate valid UUID v4 strings."""
    hex_chars = "0123456789abcdef"
    return st.tuples(
        st.text(alphabet=hex_chars, min_size=8, max_size=8),
        st.text(alphabet=hex_chars, min_size=4, max_size=4),
        st.text(alphabet=hex_chars, min_size=3, max_size=3),
        st.sampled_from(list("89ab")),
        st.text(alphabet=hex_chars, min_size=3, max_size=3),
        st.text(alphabet=hex_chars, min_size=12, max_size=12),
    ).map(lambda t: f"{t[0]}-{t[1]}-4{t[2]}-{t[3]}{t[4]}-{t[5]}")


def _bedrock_generate_response():
    """Build a mock Bedrock response for generate_handler."""
    questions = [{"step": 1, "type": "free_text", "prompt": "テスト設問", "options": None, "context": None}]
    return {"content": [{"text": json.dumps({"questions": questions}, ensure_ascii=False)}]}


def _bedrock_grade_response():
    """Build a mock Bedrock response for grade_handler."""
    return {"content": [{"text": json.dumps({"passed": True, "score": 80})}]}


@given(session_id=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()))
@settings(max_examples=100)
def test_generate_no_auth_required(session_id):
    """Property 8 (generate): 認証なしアクセス

    任意のリクエストに対して、Authorizationヘッダーなしで
    POST /lv1/generate が正常処理されることを検証。

    **Validates: Requirements 7.3**
    """
    event = {
        "body": json.dumps({"session_id": session_id}),
        "headers": {},  # No Authorization header
    }

    with patch("backend.handlers.generate_handler.invoke_claude") as mock_invoke:
        mock_invoke.return_value = _bedrock_generate_response()
        resp = generate_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "questions" in body


@given(
    session_id=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
    answer=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
)
@settings(max_examples=100)
def test_grade_no_auth_required(session_id, answer):
    """Property 8 (grade): 認証なしアクセス

    任意のリクエストに対して、Authorizationヘッダーなしで
    POST /lv1/grade が正常処理されることを検証。

    **Validates: Requirements 7.3**
    """
    event = {
        "body": json.dumps({
            "session_id": session_id,
            "step": 1,
            "question": {"step": 1, "type": "free_text", "prompt": "テスト"},
            "answer": answer,
        }),
        "headers": {},
    }

    with (
        patch("backend.handlers.grade_handler.invoke_claude") as mock_invoke,
        patch("backend.handlers.grade_handler.generate_feedback") as mock_review,
    ):
        mock_invoke.return_value = _bedrock_grade_response()
        mock_review.return_value = {"feedback": "Good", "explanation": "Explanation"}
        resp = grade_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "passed" in body
    assert "score" in body


@given(session_id=_uuid_v4_strategy())
@settings(max_examples=100)
def test_complete_no_auth_required(session_id):
    """Property 8 (complete): 認証なしアクセス

    任意のリクエストに対して、Authorizationヘッダーなしで
    POST /lv1/complete が正常処理されることを検証。

    **Validates: Requirements 7.3**
    """
    event = {
        "body": json.dumps({
            "session_id": session_id,
            "questions": [{"step": 1, "type": "free_text", "prompt": "Q"}],
            "answers": ["A"],
            "grades": [{"passed": True, "score": 80}],
            "final_passed": True,
        }),
        "headers": {},
    }

    mock_dynamodb = MagicMock()
    mock_table = MagicMock()
    mock_dynamodb.Table.return_value = mock_table

    with patch("backend.handlers.complete_handler._get_dynamodb_resource", return_value=mock_dynamodb):
        resp = complete_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["saved"] is True


@given(session_id=_uuid_v4_strategy())
@settings(max_examples=100)
def test_gate_no_auth_required(session_id):
    """Property 8 (gate): 認証なしアクセス

    任意のリクエストに対して、Authorizationヘッダーなしで
    GET /levels/status が正常処理されることを検証。

    **Validates: Requirements 7.3**
    """
    event = {
        "queryStringParameters": {"session_id": session_id},
        "headers": {},
    }

    mock_dynamodb = MagicMock()
    mock_table = MagicMock()
    mock_table.get_item.return_value = {}
    mock_dynamodb.Table.return_value = mock_table

    with patch("backend.handlers.gate_handler._get_dynamodb_resource", return_value=mock_dynamodb):
        resp = gate_handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert "levels" in body
