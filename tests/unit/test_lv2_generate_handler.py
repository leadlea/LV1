"""Unit tests for backend/handlers/lv2_generate_handler.py"""

import json
from unittest.mock import patch

import pytest

from backend.handlers.lv2_generate_handler import (
    handler,
    _parse_questions,
    STEP_TYPE_MAP,
)


def _make_question(step: int, q_type: str, prompt: str = "設問文", context="業務シナリオ"):
    """Helper to build a single question dict."""
    return {
        "step": step,
        "type": q_type,
        "prompt": prompt,
        "options": None,
        "context": context,
    }


def _valid_questions(overrides: dict | None = None):
    """Build a list of 4 valid LV2 questions. overrides keyed by step (1-based)."""
    qs = [
        _make_question(1, "scenario", "業務プロセス設計の設問", "業務シナリオ説明"),
        _make_question(2, "free_text", "AI実行指示の設問", "文脈説明"),
        _make_question(3, "scenario", "成果物検証の設問", "成果物サンプル"),
        _make_question(4, "free_text", "改善サイクルの設問", "振り返り文脈"),
    ]
    if overrides:
        for step, patch_dict in overrides.items():
            qs[step - 1].update(patch_dict)
    return qs


def _bedrock_response(questions, stop_reason="end_turn"):
    """Build a mock Bedrock response dict."""
    return {
        "content": [{"text": json.dumps({"questions": questions}, ensure_ascii=False)}],
        "stop_reason": stop_reason,
    }


def _api_event(body: dict) -> dict:
    return {"body": json.dumps(body)}


# ---------------------------------------------------------------------------
# Task 4.1: context が null の場合の寛容化テスト
# ---------------------------------------------------------------------------
class TestParseQuestionsNullContext:
    """_parse_questions should treat context=null as empty string, not raise."""

    def test_null_context_does_not_raise(self):
        qs = _valid_questions(overrides={1: {"context": None}})
        result = _bedrock_response(qs)

        parsed = _parse_questions(result)

        assert len(parsed) == 4
        assert parsed[0]["context"] == ""

    def test_null_context_on_multiple_steps(self):
        qs = _valid_questions(overrides={
            1: {"context": None},
            3: {"context": None},
        })
        result = _bedrock_response(qs)

        parsed = _parse_questions(result)

        assert parsed[0]["context"] == ""
        assert parsed[2]["context"] == ""
        # Non-null contexts preserved
        assert parsed[1]["context"] == "文脈説明"
        assert parsed[3]["context"] == "振り返り文脈"


# ---------------------------------------------------------------------------
# Task 4.2: type 正規化テスト
# ---------------------------------------------------------------------------
class TestParseQuestionsTypeNormalization:
    """_parse_questions should normalize type via .strip().lower()."""

    def test_capitalized_type_accepted(self):
        qs = _valid_questions(overrides={1: {"type": "Scenario"}})
        result = _bedrock_response(qs)

        parsed = _parse_questions(result)

        assert parsed[0]["type"] == "scenario"

    def test_type_with_surrounding_spaces_accepted(self):
        qs = _valid_questions(overrides={1: {"type": " scenario "}})
        result = _bedrock_response(qs)

        parsed = _parse_questions(result)

        assert parsed[0]["type"] == "scenario"

    def test_uppercase_free_text_accepted(self):
        qs = _valid_questions(overrides={2: {"type": "FREE_TEXT"}})
        result = _bedrock_response(qs)

        parsed = _parse_questions(result)

        assert parsed[1]["type"] == "free_text"


# ---------------------------------------------------------------------------
# Task 4.3: 不完全JSON（切断シミュレート）テスト
# ---------------------------------------------------------------------------
class TestParseQuestionsTruncatedJson:
    """_parse_questions should raise ValueError on truncated/incomplete JSON."""

    def test_truncated_json_raises_value_error(self):
        truncated_text = '{"questions":[{"step":1,"type":"scenario","prompt":"設問","options":null,"context":"シナリオ"},{"step":2'
        result = {
            "content": [{"text": truncated_text}],
            "stop_reason": "max_tokens",
        }

        with pytest.raises(ValueError, match="not valid JSON"):
            _parse_questions(result)


# ---------------------------------------------------------------------------
# Task 4.4: handler が invoke_claude を max_tokens=4096 で呼ぶことの確認
# ---------------------------------------------------------------------------
class TestHandlerMaxTokens:
    """handler should call invoke_claude with max_tokens=4096."""

    @patch("backend.handlers.lv2_generate_handler.invoke_claude")
    def test_invoke_claude_called_with_max_tokens_4096(self, mock_invoke):
        mock_invoke.return_value = _bedrock_response(_valid_questions())

        resp = handler(_api_event({"session_id": "test-session"}), None)

        assert resp["statusCode"] == 200
        mock_invoke.assert_called_once()
        call_args = mock_invoke.call_args
        assert call_args[1].get("max_tokens") == 4096 or (
            len(call_args[0]) >= 3 and call_args[0][2] == 4096
        )
