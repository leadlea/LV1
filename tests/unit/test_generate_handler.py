"""Unit tests for backend/handlers/generate_handler.py"""

import json
from unittest.mock import patch, MagicMock

import pytest

from backend.handlers.generate_handler import handler, _parse_questions, SYSTEM_PROMPT


def _bedrock_response(questions_data):
    """Build a mock Bedrock response with the given questions payload."""
    return {
        "content": [{"text": json.dumps({"questions": questions_data})}]
    }


VALID_QUESTIONS = [
    {"step": 1, "type": "multiple_choice", "prompt": "Q1?", "options": ["A", "B"], "context": None},
    {"step": 2, "type": "free_text", "prompt": "Q2?", "options": None, "context": "some context"},
    {"step": 3, "type": "scenario", "prompt": "Q3?", "options": None, "context": None},
]


def _api_event(body: dict) -> dict:
    return {"body": json.dumps(body)}


class TestHandler:
    @patch("backend.handlers.generate_handler.invoke_claude")
    def test_returns_200_with_valid_questions(self, mock_invoke):
        mock_invoke.return_value = _bedrock_response(VALID_QUESTIONS)

        resp = handler(_api_event({"session_id": "abc-123"}), None)

        assert resp["statusCode"] == 200
        data = json.loads(resp["body"])
        assert data["session_id"] == "abc-123"
        assert len(data["questions"]) == 3

    def test_returns_400_for_missing_session_id(self):
        resp = handler(_api_event({}), None)
        assert resp["statusCode"] == 400

    def test_returns_400_for_invalid_json_body(self):
        resp = handler({"body": "not json"}, None)
        assert resp["statusCode"] == 400

    @patch("backend.handlers.generate_handler.invoke_claude")
    def test_returns_500_on_bedrock_failure(self, mock_invoke):
        mock_invoke.side_effect = RuntimeError("boom")

        resp = handler(_api_event({"session_id": "abc"}), None)
        assert resp["statusCode"] == 500

    @patch("backend.handlers.generate_handler.invoke_claude")
    def test_cors_header_present(self, mock_invoke):
        mock_invoke.return_value = _bedrock_response(VALID_QUESTIONS)

        resp = handler(_api_event({"session_id": "abc"}), None)
        assert resp["headers"]["Access-Control-Allow-Origin"] == "*"


class TestParseQuestions:
    def test_valid_questions_parsed(self):
        result = _bedrock_response(VALID_QUESTIONS)
        questions = _parse_questions(result)
        assert len(questions) == 3
        assert questions[0]["type"] == "multiple_choice"
        assert questions[0]["options"] == ["A", "B"]
        assert questions[1]["options"] is None  # free_text has no options

    def test_raises_on_invalid_json(self):
        with pytest.raises(ValueError):
            _parse_questions({"content": [{"text": "not json"}]})

    def test_raises_on_missing_questions_key(self):
        with pytest.raises(ValueError):
            _parse_questions({"content": [{"text": json.dumps({"other": []})}]})

    def test_raises_on_invalid_type(self):
        bad = [{"step": 1, "type": "essay", "prompt": "Q?"}]
        with pytest.raises(ValueError):
            _parse_questions(_bedrock_response(bad))

    def test_raises_on_empty_prompt(self):
        bad = [{"step": 1, "type": "free_text", "prompt": ""}]
        with pytest.raises(ValueError):
            _parse_questions(_bedrock_response(bad))
