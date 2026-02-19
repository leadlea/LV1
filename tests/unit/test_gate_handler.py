"""Unit tests for backend/handlers/gate_handler.py"""

import json
from unittest.mock import patch, MagicMock

import pytest

from backend.handlers.gate_handler import handler, _build_levels

VALID_SESSION_ID = "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"


def _api_event(session_id=None):
    params = {"session_id": session_id} if session_id else None
    return {"queryStringParameters": params}


class TestBuildLevels:
    def test_lv1_not_passed(self):
        levels = _build_levels(False)
        assert levels["lv1"] == {"unlocked": True, "passed": False}
        assert levels["lv2"] == {"unlocked": False, "passed": False}
        assert levels["lv3"] == {"unlocked": False, "passed": False}
        assert levels["lv4"] == {"unlocked": False, "passed": False}

    def test_lv1_passed(self):
        levels = _build_levels(True)
        assert levels["lv1"] == {"unlocked": True, "passed": True}
        assert levels["lv2"] == {"unlocked": True, "passed": False}
        assert levels["lv3"] == {"unlocked": False, "passed": False}
        assert levels["lv4"] == {"unlocked": False, "passed": False}


class TestHandler:
    def test_returns_400_without_session_id(self):
        resp = handler({"queryStringParameters": None}, None)
        assert resp["statusCode"] == 400

    def test_returns_400_for_invalid_session_id(self):
        resp = handler(_api_event("not-a-uuid"), None)
        assert resp["statusCode"] == 400

    @patch("backend.handlers.gate_handler._get_dynamodb_resource")
    def test_returns_200_with_default_when_no_progress(self, mock_ddb):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        mock_ddb.return_value.Table.return_value = mock_table

        resp = handler(_api_event(VALID_SESSION_ID), None)
        assert resp["statusCode"] == 200
        data = json.loads(resp["body"])
        assert data["levels"]["lv1"]["unlocked"] is True
        assert data["levels"]["lv2"]["unlocked"] is False

    @patch("backend.handlers.gate_handler._get_dynamodb_resource")
    def test_returns_lv2_unlocked_when_lv1_passed(self, mock_ddb):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {"Item": {"lv1_passed": True}}
        mock_ddb.return_value.Table.return_value = mock_table

        resp = handler(_api_event(VALID_SESSION_ID), None)
        data = json.loads(resp["body"])
        assert data["levels"]["lv2"]["unlocked"] is True

    @patch("backend.handlers.gate_handler._get_dynamodb_resource")
    def test_returns_500_on_dynamodb_error(self, mock_ddb):
        mock_ddb.side_effect = Exception("connection error")

        resp = handler(_api_event(VALID_SESSION_ID), None)
        assert resp["statusCode"] == 500

    @patch("backend.handlers.gate_handler._get_dynamodb_resource")
    def test_cors_header_present(self, mock_ddb):
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        mock_ddb.return_value.Table.return_value = mock_table

        resp = handler(_api_event(VALID_SESSION_ID), None)
        assert resp["headers"]["Access-Control-Allow-Origin"] == "*"
