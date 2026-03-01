"""Unit tests for backend/handlers/lv3_generate_handler.py"""

import json
from unittest.mock import patch

import pytest

from backend.handlers.lv3_generate_handler import (
    handler,
    _parse_questions,
    STEP_TYPE_MAP,
)


def _make_question(step: int, q_type: str, prompt: str = "設問文", context: str = "プロジェクトシナリオ"):
    """Helper to build a single question dict."""
    return {
        "step": step,
        "type": q_type,
        "prompt": prompt,
        "options": None,
        "context": context,
    }


def _valid_questions(overrides: dict | None = None):
    """Build a list of 5 valid LV3 questions. overrides keyed by step (1-based)."""
    qs = [
        _make_question(1, "scenario", "プロジェクト計画策定の設問", "計画シナリオ説明"),
        _make_question(2, "free_text", "AI活用ロードマップの設問", "ロードマップ文脈"),
        _make_question(3, "scenario", "AI導入計画立案の設問", "導入計画シナリオ"),
        _make_question(4, "scenario", "スキル育成計画の設問", "育成計画シナリオ"),
        _make_question(5, "free_text", "ROI評価改善の設問", "ROI評価文脈"),
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
# Task 3.1: handler が invoke_claude を max_tokens=4096 で呼ぶことの確認
# ---------------------------------------------------------------------------
class TestHandlerMaxTokens:
    """handler should call invoke_claude with max_tokens=4096."""

    @patch("backend.handlers.lv3_generate_handler.invoke_claude")
    def test_invoke_claude_called_with_max_tokens_4096(self, mock_invoke):
        mock_invoke.return_value = _bedrock_response(_valid_questions())

        resp = handler(_api_event({"session_id": "test-session"}), None)

        assert resp["statusCode"] == 200
        mock_invoke.assert_called_once()
        call_args = mock_invoke.call_args
        assert call_args[1].get("max_tokens") == 4096 or (
            len(call_args[0]) >= 3 and call_args[0][2] == 4096
        )

    @patch("backend.handlers.lv3_generate_handler.invoke_claude")
    def test_handler_returns_5_questions_on_success(self, mock_invoke):
        mock_invoke.return_value = _bedrock_response(_valid_questions())

        resp = handler(_api_event({"session_id": "test-session"}), None)

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["session_id"] == "test-session"
        assert len(body["questions"]) == 5




# ---------------------------------------------------------------------------
# Task 3.2: _parse_questions の stop_reason=max_tokens 検知テスト
# ---------------------------------------------------------------------------
class TestParseQuestionsMaxTokensWarning:
    """_parse_questions should log a warning when stop_reason is max_tokens."""

    def test_max_tokens_stop_reason_logs_warning(self, caplog):
        """Valid JSON with stop_reason=max_tokens should still parse but emit warning."""
        import logging

        result = _bedrock_response(_valid_questions(), stop_reason="max_tokens")

        with caplog.at_level(logging.WARNING, logger="backend.handlers.lv3_generate_handler"):
            parsed = _parse_questions(result)

        assert len(parsed) == 5
        assert any("truncated" in record.message.lower() or "max_tokens" in record.message.lower()
                    for record in caplog.records), (
            f"Expected warning about max_tokens truncation, got: {[r.message for r in caplog.records]}"
        )

    def test_end_turn_stop_reason_no_warning(self, caplog):
        """Normal stop_reason=end_turn should not emit truncation warning."""
        import logging

        result = _bedrock_response(_valid_questions(), stop_reason="end_turn")

        with caplog.at_level(logging.WARNING, logger="backend.handlers.lv3_generate_handler"):
            parsed = _parse_questions(result)

        assert len(parsed) == 5
        assert not any("truncated" in record.message.lower() or "max_tokens" in record.message.lower()
                       for record in caplog.records), (
            f"Unexpected truncation warning for end_turn: {[r.message for r in caplog.records]}"
        )

