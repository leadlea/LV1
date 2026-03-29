"""ユニットテスト: セルフチェック送信ハンドラ"""

import json
import uuid
from unittest.mock import patch, MagicMock

import pytest
from backend.handlers.selfcheck_handler import handler


def _make_answers(track="business", val=2):
    answers = {f"common_{i}": val for i in range(1, 7)}
    prefix = "biz" if track == "business" else "eng"
    for i in range(1, 7):
        answers[f"{prefix}_{i}"] = val
    return answers


def _event(body):
    return {"body": json.dumps(body)}


def _valid_body(track="business"):
    return {
        "session_id": str(uuid.uuid4()),
        "track": track,
        "answers": _make_answers(track),
    }


class TestSelfcheckHandler:
    def test_success(self):
        body = _valid_body()
        mock_table = MagicMock()
        with patch("backend.handlers.selfcheck_handler.boto3") as mock_boto3, \
             patch("backend.handlers.selfcheck_handler.generate_feedback", return_value={"strengths": "s", "improvements": "i", "next_actions": "n"}):
            mock_boto3.resource.return_value.Table.return_value = mock_table
            resp = handler(_event(body), None)
        assert resp["statusCode"] == 200
        data = json.loads(resp["body"])
        assert data["skill_level"] in ("Lv1", "Lv2", "Lv3", "Lv4", "Lv5")
        assert data["feedback"] is not None
        assert data["feedback_unavailable"] is False

    def test_feedback_failure_returns_unavailable(self):
        body = _valid_body()
        mock_table = MagicMock()
        with patch("backend.handlers.selfcheck_handler.boto3") as mock_boto3, \
             patch("backend.handlers.selfcheck_handler.generate_feedback", return_value=None):
            mock_boto3.resource.return_value.Table.return_value = mock_table
            resp = handler(_event(body), None)
        assert resp["statusCode"] == 200
        data = json.loads(resp["body"])
        assert data["feedback"] is None
        assert data["feedback_unavailable"] is True

    def test_invalid_json(self):
        resp = handler({"body": "not json"}, None)
        assert resp["statusCode"] == 400

    def test_invalid_session_id(self):
        body = _valid_body()
        body["session_id"] = "not-a-uuid"
        resp = handler(_event(body), None)
        assert resp["statusCode"] == 400

    def test_invalid_track(self):
        body = _valid_body()
        body["track"] = "invalid"
        resp = handler(_event(body), None)
        assert resp["statusCode"] == 400

    def test_invalid_answers(self):
        body = _valid_body()
        body["answers"]["common_1"] = 99
        resp = handler(_event(body), None)
        assert resp["statusCode"] == 400

    def test_dynamo_failure(self):
        body = _valid_body()
        mock_table = MagicMock()
        mock_table.put_item.side_effect = Exception("DynamoDB error")
        with patch("backend.handlers.selfcheck_handler.boto3") as mock_boto3, \
             patch("backend.handlers.selfcheck_handler.generate_feedback", return_value=None):
            mock_boto3.resource.return_value.Table.return_value = mock_table
            resp = handler(_event(body), None)
        assert resp["statusCode"] == 500

    def test_cors_headers(self):
        body = _valid_body()
        mock_table = MagicMock()
        with patch("backend.handlers.selfcheck_handler.boto3") as mock_boto3, \
             patch("backend.handlers.selfcheck_handler.generate_feedback", return_value=None):
            mock_boto3.resource.return_value.Table.return_value = mock_table
            resp = handler(_event(body), None)
        assert resp["headers"]["Access-Control-Allow-Origin"] == "*"
