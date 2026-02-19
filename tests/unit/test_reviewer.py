"""Unit tests for backend/lib/reviewer.py"""

import json
from unittest.mock import patch

import pytest

from backend.lib.reviewer import generate_feedback


def _bedrock_response(data):
    return {"content": [{"text": json.dumps(data, ensure_ascii=False)}]}


QUESTION = {"step": 1, "type": "free_text", "prompt": "テスト設問"}
ANSWER = "テスト回答"
GRADE = {"passed": True, "score": 80}


class TestGenerateFeedback:
    @patch("backend.lib.reviewer.invoke_claude")
    def test_returns_feedback_and_explanation(self, mock_invoke):
        mock_invoke.return_value = _bedrock_response({
            "feedback": "良い回答です",
            "explanation": "正解の考え方は...",
        })

        result = generate_feedback(QUESTION, ANSWER, GRADE)

        assert result["feedback"] == "良い回答です"
        assert result["explanation"] == "正解の考え方は..."

    @patch("backend.lib.reviewer.invoke_claude")
    def test_raises_on_invalid_json(self, mock_invoke):
        mock_invoke.return_value = {"content": [{"text": "not json"}]}

        with pytest.raises(ValueError, match="not valid JSON"):
            generate_feedback(QUESTION, ANSWER, GRADE)

    @patch("backend.lib.reviewer.invoke_claude")
    def test_raises_on_empty_feedback(self, mock_invoke):
        mock_invoke.return_value = _bedrock_response({
            "feedback": "",
            "explanation": "解説",
        })

        with pytest.raises(ValueError, match="feedback"):
            generate_feedback(QUESTION, ANSWER, GRADE)

    @patch("backend.lib.reviewer.invoke_claude")
    def test_raises_on_empty_explanation(self, mock_invoke):
        mock_invoke.return_value = _bedrock_response({
            "feedback": "フィードバック",
            "explanation": "",
        })

        with pytest.raises(ValueError, match="explanation"):
            generate_feedback(QUESTION, ANSWER, GRADE)
