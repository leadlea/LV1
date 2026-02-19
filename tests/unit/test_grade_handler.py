"""Unit tests for backend/handlers/grade_handler.py"""

import json
from unittest.mock import patch

import pytest

from backend.handlers.grade_handler import handler, _parse_grade_result


def _bedrock_grade_response(passed, score):
    return {"content": [{"text": json.dumps({"passed": passed, "score": score})}]}


def _api_event(body: dict) -> dict:
    return {"body": json.dumps(body)}


VALID_BODY = {
    "session_id": "abc-123",
    "step": 1,
    "question": {"step": 1, "type": "free_text", "prompt": "Q?"},
    "answer": "My answer",
}


class TestHandler:
    @patch("backend.handlers.grade_handler.generate_feedback")
    @patch("backend.handlers.grade_handler.invoke_claude")
    def test_returns_200_with_grade_and_review(self, mock_invoke, mock_review):
        mock_invoke.return_value = _bedrock_grade_response(True, 85)
        mock_review.return_value = {"feedback": "Good", "explanation": "Because..."}

        resp = handler(_api_event(VALID_BODY), None)

        assert resp["statusCode"] == 200
        data = json.loads(resp["body"])
        assert data["session_id"] == "abc-123"
        assert data["step"] == 1
        assert data["passed"] is True
        assert data["score"] == 85
        assert data["feedback"] == "Good"
        assert data["explanation"] == "Because..."

    def test_returns_400_for_missing_session_id(self):
        body = {**VALID_BODY}
        del body["session_id"]
        resp = handler(_api_event(body), None)
        assert resp["statusCode"] == 400

    def test_returns_400_for_missing_step(self):
        body = {**VALID_BODY, "step": "not_int"}
        resp = handler(_api_event(body), None)
        assert resp["statusCode"] == 400

    def test_returns_400_for_missing_question(self):
        body = {**VALID_BODY, "question": "not_dict"}
        resp = handler(_api_event(body), None)
        assert resp["statusCode"] == 400

    def test_returns_400_for_empty_answer(self):
        body = {**VALID_BODY, "answer": "  "}
        resp = handler(_api_event(body), None)
        assert resp["statusCode"] == 400

    def test_returns_400_for_invalid_json_body(self):
        resp = handler({"body": "not json"}, None)
        assert resp["statusCode"] == 400

    @patch("backend.handlers.grade_handler.invoke_claude")
    def test_returns_500_on_bedrock_failure(self, mock_invoke):
        mock_invoke.side_effect = RuntimeError("boom")
        resp = handler(_api_event(VALID_BODY), None)
        assert resp["statusCode"] == 500

    @patch("backend.handlers.grade_handler.generate_feedback")
    @patch("backend.handlers.grade_handler.invoke_claude")
    def test_cors_header_present(self, mock_invoke, mock_review):
        mock_invoke.return_value = _bedrock_grade_response(True, 90)
        mock_review.return_value = {"feedback": "OK", "explanation": "OK"}

        resp = handler(_api_event(VALID_BODY), None)
        assert resp["headers"]["Access-Control-Allow-Origin"] == "*"


class TestParseGradeResult:
    def test_valid_result(self):
        result = _parse_grade_result(_bedrock_grade_response(True, 75))
        assert result == {"passed": True, "score": 75}

    def test_raises_on_invalid_json(self):
        with pytest.raises(ValueError, match="not valid JSON"):
            _parse_grade_result({"content": [{"text": "bad"}]})

    def test_raises_on_non_bool_passed(self):
        with pytest.raises(ValueError, match="passed"):
            _parse_grade_result(_bedrock_grade_response("yes", 50))

    def test_raises_on_score_out_of_range(self):
        with pytest.raises(ValueError, match="score"):
            _parse_grade_result(_bedrock_grade_response(True, 150))
