"""Unit tests for backend/lib/threshold_resolver.py and handler integration."""

import json
import os
from unittest.mock import patch

import pytest

from backend.lib.threshold_resolver import get_threshold, resolve_passed


# ---------------------------------------------------------------------------
# Task 5.1: get_threshold unit tests
# ---------------------------------------------------------------------------


class TestGetThreshold:
    def test_default_threshold_when_env_not_set(self):
        """環境変数未設定時にデフォルト30が返ること。"""
        with patch.dict(os.environ, {}, clear=True):
            assert get_threshold(1) == 30

    def test_non_integer_string_fallback(self):
        """非整数文字列のときデフォルト30が返ること。"""
        with patch.dict(os.environ, {"PASS_THRESHOLD_LV1": "abc"}):
            assert get_threshold(1) == 30

    def test_empty_string_fallback(self):
        """空文字列のときデフォルト30が返ること。"""
        with patch.dict(os.environ, {"PASS_THRESHOLD_LV1": ""}):
            assert get_threshold(1) == 30

    def test_boundary_value_zero(self):
        """境界値0が正しく返ること。"""
        with patch.dict(os.environ, {"PASS_THRESHOLD_LV1": "0"}):
            assert get_threshold(1) == 0

    def test_boundary_value_hundred(self):
        """境界値100が正しく返ること。"""
        with patch.dict(os.environ, {"PASS_THRESHOLD_LV1": "100"}):
            assert get_threshold(1) == 100

    def test_negative_value_clamped_to_zero(self):
        """負の値が0に補正されること。"""
        with patch.dict(os.environ, {"PASS_THRESHOLD_LV1": "-10"}):
            assert get_threshold(1) == 0

    def test_above_hundred_clamped(self):
        """100超の値が100に補正されること。"""
        with patch.dict(os.environ, {"PASS_THRESHOLD_LV1": "150"}):
            assert get_threshold(1) == 100

    def test_valid_threshold(self):
        """有効な閾値50が正しく返ること。"""
        with patch.dict(os.environ, {"PASS_THRESHOLD_LV1": "50"}):
            assert get_threshold(1) == 50


# ---------------------------------------------------------------------------
# Task 5.2: Handler integration – each handler calls resolve_passed with
#            the correct level number
# ---------------------------------------------------------------------------


def _bedrock_grade_response(passed: bool, score: int) -> dict:
    return {"content": [{"text": json.dumps({"passed": passed, "score": score})}]}


def _api_event(body: dict) -> dict:
    return {"body": json.dumps(body)}


_LV1_BODY = {
    "session_id": "s-1",
    "step": 1,
    "question": {"step": 1, "type": "free_text", "prompt": "Q?"},
    "answer": "A",
}

_LV2_BODY = {**_LV1_BODY, "step": 1}
_LV3_BODY = {**_LV1_BODY, "step": 1}
_LV4_BODY = {**_LV1_BODY, "step": 1}


class TestHandlerLevelIntegration:
    @patch("backend.handlers.grade_handler.generate_feedback",
           return_value={"feedback": "ok", "explanation": "ok"})
    @patch("backend.handlers.grade_handler.invoke_claude")
    @patch("backend.handlers.grade_handler.resolve_passed")
    def test_grade_handler_uses_level_1(self, mock_resolve, mock_invoke, _mock_review):
        mock_invoke.return_value = _bedrock_grade_response(True, 70)
        mock_resolve.return_value = True

        from backend.handlers.grade_handler import handler as lv1_handler
        lv1_handler(_api_event(_LV1_BODY), None)

        mock_resolve.assert_called_once_with(level=1, score=70)

    @patch("backend.handlers.lv2_grade_handler.generate_lv2_feedback",
           return_value={"feedback": "ok", "explanation": "ok"})
    @patch("backend.handlers.lv2_grade_handler.invoke_claude")
    @patch("backend.handlers.lv2_grade_handler.resolve_passed")
    def test_lv2_grade_handler_uses_level_2(self, mock_resolve, mock_invoke, _mock_review):
        mock_invoke.return_value = _bedrock_grade_response(True, 70)
        mock_resolve.return_value = True

        from backend.handlers.lv2_grade_handler import handler as lv2_handler
        lv2_handler(_api_event(_LV2_BODY), None)

        mock_resolve.assert_called_once_with(level=2, score=70)

    @patch("backend.handlers.lv3_grade_handler.generate_lv3_feedback",
           return_value={"feedback": "ok", "explanation": "ok"})
    @patch("backend.handlers.lv3_grade_handler.invoke_claude")
    @patch("backend.handlers.lv3_grade_handler.resolve_passed")
    def test_lv3_grade_handler_uses_level_3(self, mock_resolve, mock_invoke, _mock_review):
        mock_invoke.return_value = _bedrock_grade_response(True, 70)
        mock_resolve.return_value = True

        from backend.handlers.lv3_grade_handler import handler as lv3_handler
        lv3_handler(_api_event(_LV3_BODY), None)

        mock_resolve.assert_called_once_with(level=3, score=70)

    @patch("backend.handlers.lv4_grade_handler.generate_lv4_feedback",
           return_value={"feedback": "ok", "explanation": "ok"})
    @patch("backend.handlers.lv4_grade_handler.invoke_claude")
    @patch("backend.handlers.lv4_grade_handler.resolve_passed")
    def test_lv4_grade_handler_uses_level_4(self, mock_resolve, mock_invoke, _mock_review):
        mock_invoke.return_value = _bedrock_grade_response(True, 70)
        mock_resolve.return_value = True

        from backend.handlers.lv4_grade_handler import handler as lv4_handler
        lv4_handler(_api_event(_LV4_BODY), None)

        mock_resolve.assert_called_once_with(level=4, score=70)
