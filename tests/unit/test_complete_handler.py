"""Unit tests for backend/handlers/complete_handler.py"""

import json
from unittest.mock import patch, MagicMock

import pytest

from backend.handlers.complete_handler import handler, _validate_body


def _api_event(body: dict) -> dict:
    return {"body": json.dumps(body)}


VALID_BODY = {
    "session_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",
    "questions": [{"step": 1, "type": "free_text", "prompt": "Q?"}],
    "answers": ["My answer"],
    "grades": [{"passed": True, "score": 85}],
    "final_passed": True,
}


class TestValidateBody:
    def test_valid_body_returns_none(self):
        assert _validate_body(VALID_BODY) is None

    @pytest.mark.parametrize("field", [
        "session_id", "questions", "answers", "grades", "final_passed",
    ])
    def test_missing_required_field(self, field):
        body = {**VALID_BODY}
        del body[field]
        assert _validate_body(body) is not None

    def test_invalid_session_id_format(self):
        body = {**VALID_BODY, "session_id": "not-a-uuid"}
        assert "UUID" in _validate_body(body)

    def test_empty_questions_list(self):
        body = {**VALID_BODY, "questions": []}
        assert _validate_body(body) is not None

    def test_final_passed_not_bool(self):
        body = {**VALID_BODY, "final_passed": "yes"}
        assert _validate_body(body) is not None


class TestHandler:
    @patch("backend.handlers.complete_handler._get_dynamodb_resource")
    def test_returns_200_on_success(self, mock_ddb):
        mock_table = MagicMock()
        mock_ddb.return_value.Table.return_value = mock_table

        resp = handler(_api_event(VALID_BODY), None)

        assert resp["statusCode"] == 200
        data = json.loads(resp["body"])
        assert data["saved"] is True
        assert "record_id" in data

    @patch("backend.handlers.complete_handler._get_dynamodb_resource")
    def test_saves_to_results_and_progress_tables(self, mock_ddb):
        mock_table = MagicMock()
        mock_ddb.return_value.Table.return_value = mock_table

        handler(_api_event(VALID_BODY), None)

        assert mock_table.put_item.call_count == 2

    def test_returns_400_for_invalid_json(self):
        resp = handler({"body": "not json"}, None)
        assert resp["statusCode"] == 400

    def test_returns_400_for_missing_session_id(self):
        body = {**VALID_BODY}
        del body["session_id"]
        resp = handler(_api_event(body), None)
        assert resp["statusCode"] == 400

    def test_returns_400_for_missing_final_passed(self):
        body = {**VALID_BODY}
        del body["final_passed"]
        resp = handler(_api_event(body), None)
        assert resp["statusCode"] == 400

    @patch("backend.handlers.complete_handler._get_dynamodb_resource")
    def test_returns_500_on_dynamodb_error(self, mock_ddb):
        from botocore.exceptions import ClientError

        mock_table = MagicMock()
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "InternalServerError", "Message": "fail"}},
            "PutItem",
        )
        mock_ddb.return_value.Table.return_value = mock_table

        resp = handler(_api_event(VALID_BODY), None)
        assert resp["statusCode"] == 500
        data = json.loads(resp["body"])
        assert "リトライ" in data["error"]

    @patch("backend.handlers.complete_handler._get_dynamodb_resource")
    def test_cors_header_present(self, mock_ddb):
        mock_table = MagicMock()
        mock_ddb.return_value.Table.return_value = mock_table

        resp = handler(_api_event(VALID_BODY), None)
        assert resp["headers"]["Access-Control-Allow-Origin"] == "*"
