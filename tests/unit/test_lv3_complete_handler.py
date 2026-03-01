"""Unit tests for backend/handlers/lv3_complete_handler.py - LV1 progress update logic"""

import json
from unittest.mock import patch, MagicMock

import pytest

from backend.handlers.lv3_complete_handler import handler, _update_progress


LV3_SESSION_ID = "c3d4e5f6-a7b8-4c9d-8e1f-2a3b4c5d6e7f"
LV1_SESSION_ID = "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e"


def _api_event(body: dict) -> dict:
    return {"body": json.dumps(body)}


VALID_BODY = {
    "session_id": LV3_SESSION_ID,
    "lv1_session_id": LV1_SESSION_ID,
    "questions": [{"step": 1, "type": "free_text", "prompt": "Q?"}],
    "answers": ["My answer"],
    "grades": [{"passed": True, "score": 85}],
    "final_passed": True,
}


def _make_mock_table(existing_items=None):
    """Create a mock DynamoDB table that returns existing items on get_item."""
    mock_table = MagicMock()
    if existing_items is None:
        existing_items = {}

    def get_item_side_effect(Key):
        pk = Key["PK"]
        return {"Item": existing_items[pk]} if pk in existing_items else {}

    mock_table.get_item.side_effect = get_item_side_effect
    return mock_table


class TestUpdateProgressWithLv1SessionId:
    """Task 5.1: LV1セッションIDのプログレスが正しく更新されるテスト"""

    def test_lv1_progress_lv3_passed_set_true_when_final_passed(self):
        """When final_passed=True and lv1_session_id is provided, LV1 progress should have lv3_passed=True."""
        lv1_existing = {
            "PK": f"SESSION#{LV1_SESSION_ID}",
            "SK": "PROGRESS",
            "session_id": LV1_SESSION_ID,
            "lv1_passed": True,
            "lv2_passed": True,
            "lv3_passed": False,
            "lv4_passed": False,
        }
        mock_table = _make_mock_table({
            f"SESSION#{LV3_SESSION_ID}": {},
            f"SESSION#{LV1_SESSION_ID}": lv1_existing,
        })
        mock_ddb = MagicMock()
        mock_ddb.Table.return_value = mock_table

        _update_progress(mock_ddb, LV3_SESSION_ID, True, "2024-01-01T00:00:00+00:00", lv1_session_id=LV1_SESSION_ID)

        lv1_put_calls = [
            c for c in mock_table.put_item.call_args_list
            if c[1]["Item"]["PK"] == f"SESSION#{LV1_SESSION_ID}"
        ]
        assert len(lv1_put_calls) == 1
        lv1_item = lv1_put_calls[0][1]["Item"]
        assert lv1_item["lv3_passed"] is True

    def test_lv3_progress_also_updated(self):
        """LV3 session's own progress should still be updated alongside LV1."""
        mock_table = _make_mock_table({})
        mock_ddb = MagicMock()
        mock_ddb.Table.return_value = mock_table

        _update_progress(mock_ddb, LV3_SESSION_ID, True, "2024-01-01T00:00:00+00:00", lv1_session_id=LV1_SESSION_ID)

        # Should have 2 put_item calls: one for LV3 session, one for LV1 session
        assert mock_table.put_item.call_count == 2

        lv3_put_calls = [
            c for c in mock_table.put_item.call_args_list
            if c[1]["Item"]["PK"] == f"SESSION#{LV3_SESSION_ID}"
        ]
        assert len(lv3_put_calls) == 1
        assert lv3_put_calls[0][1]["Item"]["lv3_passed"] is True

    @patch("backend.handlers.lv3_complete_handler._get_dynamodb_resource")
    def test_handler_passes_lv1_session_id_to_update_progress(self, mock_ddb):
        """Handler should extract lv1_session_id from body and pass it to _update_progress."""
        mock_table = _make_mock_table({})
        mock_ddb.return_value.Table.return_value = mock_table

        resp = handler(_api_event(VALID_BODY), None)

        assert resp["statusCode"] == 200
        # Verify LV1 progress was written
        lv1_put_calls = [
            c for c in mock_table.put_item.call_args_list
            if c[1]["Item"].get("PK") == f"SESSION#{LV1_SESSION_ID}"
        ]
        assert len(lv1_put_calls) >= 1
        lv1_item = lv1_put_calls[0][1]["Item"]
        assert lv1_item["lv3_passed"] is True


class TestFallbackWithoutLv1SessionId:
    """Task 5.2: lv1_session_id が欠落している場合のフォールバック動作テスト
    Validates: Requirements 2.1
    """

    def test_only_lv3_progress_updated_when_lv1_session_id_missing(self):
        """When lv1_session_id is not provided, only LV3 session progress is updated (put_item called once)."""
        mock_table = _make_mock_table({})
        mock_ddb = MagicMock()
        mock_ddb.Table.return_value = mock_table

        _update_progress(mock_ddb, LV3_SESSION_ID, True, "2024-01-01T00:00:00+00:00", lv1_session_id=None)

        assert mock_table.put_item.call_count == 1
        put_item = mock_table.put_item.call_args_list[0][1]["Item"]
        assert put_item["PK"] == f"SESSION#{LV3_SESSION_ID}"
        assert put_item["lv3_passed"] is True

    @patch("backend.handlers.lv3_complete_handler._get_dynamodb_resource")
    def test_handler_returns_200_without_lv1_session_id(self, mock_ddb):
        """Handler returns 200 success even when lv1_session_id is absent from the request body."""
        mock_table = _make_mock_table({})
        mock_ddb.return_value.Table.return_value = mock_table

        body_without_lv1 = {
            "session_id": LV3_SESSION_ID,
            "questions": [{"step": 1, "type": "free_text", "prompt": "Q?"}],
            "answers": ["My answer"],
            "grades": [{"passed": True, "score": 85}],
            "final_passed": True,
        }
        resp = handler(_api_event(body_without_lv1), None)

        assert resp["statusCode"] == 200
        result = json.loads(resp["body"])
        assert result["saved"] is True

    @patch("backend.handlers.lv3_complete_handler._get_dynamodb_resource")
    def test_handler_no_lv1_progress_write_when_lv1_session_id_absent(self, mock_ddb):
        """When lv1_session_id is not in the body, no LV1 progress record is written (backward compat)."""
        mock_table = _make_mock_table({})
        mock_ddb.return_value.Table.return_value = mock_table

        body_without_lv1 = {
            "session_id": LV3_SESSION_ID,
            "questions": [{"step": 1, "type": "free_text", "prompt": "Q?"}],
            "answers": ["My answer"],
            "grades": [{"passed": True, "score": 85}],
            "final_passed": True,
        }
        handler(_api_event(body_without_lv1), None)

        # Only LV3 session progress should be written — no LV1 session writes
        progress_puts = [
            c for c in mock_table.put_item.call_args_list
            if c[1]["Item"].get("SK") == "PROGRESS"
        ]
        assert len(progress_puts) == 1
        assert progress_puts[0][1]["Item"]["PK"] == f"SESSION#{LV3_SESSION_ID}"


class TestFinalPassedFalseDoesNotSetLv3PassedTrue:
    """Task 5.3: final_passed: false の場合に lv3_passed が true にならないテスト
    Validates: Requirements 3.4
    """

    def test_lv1_progress_lv3_passed_false_when_final_passed_false(self):
        """When final_passed=False and lv1_session_id is provided, LV1 progress should have lv3_passed=False."""
        lv1_existing = {
            "PK": f"SESSION#{LV1_SESSION_ID}",
            "SK": "PROGRESS",
            "session_id": LV1_SESSION_ID,
            "lv1_passed": True,
            "lv2_passed": True,
            "lv3_passed": False,
            "lv4_passed": False,
        }
        mock_table = _make_mock_table({
            f"SESSION#{LV3_SESSION_ID}": {},
            f"SESSION#{LV1_SESSION_ID}": lv1_existing,
        })
        mock_ddb = MagicMock()
        mock_ddb.Table.return_value = mock_table

        _update_progress(mock_ddb, LV3_SESSION_ID, False, "2024-01-01T00:00:00+00:00", lv1_session_id=LV1_SESSION_ID)

        lv1_put_calls = [
            c for c in mock_table.put_item.call_args_list
            if c[1]["Item"]["PK"] == f"SESSION#{LV1_SESSION_ID}"
        ]
        assert len(lv1_put_calls) == 1
        lv1_item = lv1_put_calls[0][1]["Item"]
        assert lv1_item["lv3_passed"] is False

    def test_lv3_progress_lv3_passed_false_when_final_passed_false(self):
        """When final_passed=False, LV3 session progress should have lv3_passed=False."""
        mock_table = _make_mock_table({})
        mock_ddb = MagicMock()
        mock_ddb.Table.return_value = mock_table

        _update_progress(mock_ddb, LV3_SESSION_ID, False, "2024-01-01T00:00:00+00:00", lv1_session_id=LV1_SESSION_ID)

        lv3_put_calls = [
            c for c in mock_table.put_item.call_args_list
            if c[1]["Item"]["PK"] == f"SESSION#{LV3_SESSION_ID}"
        ]
        assert len(lv3_put_calls) == 1
        assert lv3_put_calls[0][1]["Item"]["lv3_passed"] is False


class TestExistingProgressPreservation:
    """Task 5.4: 既存プログレス（lv1_passed、lv2_passed、lv4_passed）が上書きされないテスト
    Validates: Requirements 3.3, 3.5
    """

    def test_lv1_passed_preserved_in_lv1_progress(self):
        """When LV1 progress already has lv1_passed=True, it should be preserved after _update_progress."""
        lv1_existing = {
            "PK": f"SESSION#{LV1_SESSION_ID}",
            "SK": "PROGRESS",
            "session_id": LV1_SESSION_ID,
            "lv1_passed": True,
            "lv2_passed": True,
            "lv3_passed": False,
            "lv4_passed": True,
        }
        mock_table = _make_mock_table({
            f"SESSION#{LV3_SESSION_ID}": {},
            f"SESSION#{LV1_SESSION_ID}": lv1_existing,
        })
        mock_ddb = MagicMock()
        mock_ddb.Table.return_value = mock_table

        _update_progress(mock_ddb, LV3_SESSION_ID, True, "2024-01-01T00:00:00+00:00", lv1_session_id=LV1_SESSION_ID)

        lv1_put_calls = [
            c for c in mock_table.put_item.call_args_list
            if c[1]["Item"]["PK"] == f"SESSION#{LV1_SESSION_ID}"
        ]
        assert len(lv1_put_calls) == 1
        lv1_item = lv1_put_calls[0][1]["Item"]
        assert lv1_item["lv1_passed"] is True
        assert lv1_item["lv2_passed"] is True
        assert lv1_item["lv4_passed"] is True
        assert lv1_item["lv3_passed"] is True

    def test_only_lv3_passed_changes_others_intact(self):
        """Only lv3_passed should change; lv1_passed, lv2_passed, lv4_passed must remain unchanged."""
        lv1_existing = {
            "PK": f"SESSION#{LV1_SESSION_ID}",
            "SK": "PROGRESS",
            "session_id": LV1_SESSION_ID,
            "lv1_passed": True,
            "lv2_passed": True,
            "lv3_passed": False,
            "lv4_passed": True,
        }
        mock_table = _make_mock_table({
            f"SESSION#{LV3_SESSION_ID}": {},
            f"SESSION#{LV1_SESSION_ID}": lv1_existing,
        })
        mock_ddb = MagicMock()
        mock_ddb.Table.return_value = mock_table

        _update_progress(mock_ddb, LV3_SESSION_ID, True, "2024-01-01T00:00:00+00:00", lv1_session_id=LV1_SESSION_ID)

        lv1_put_calls = [
            c for c in mock_table.put_item.call_args_list
            if c[1]["Item"]["PK"] == f"SESSION#{LV1_SESSION_ID}"
        ]
        lv1_item = lv1_put_calls[0][1]["Item"]

        # These must match the original existing values exactly
        assert lv1_item["lv1_passed"] == lv1_existing["lv1_passed"]
        assert lv1_item["lv2_passed"] == lv1_existing["lv2_passed"]
        assert lv1_item["lv4_passed"] == lv1_existing["lv4_passed"]
        # Only lv3_passed should have changed
        assert lv1_item["lv3_passed"] is True

    def test_existing_false_values_also_preserved(self):
        """When existing progress has some fields as False, those False values should also be preserved (not defaulted)."""
        lv1_existing = {
            "PK": f"SESSION#{LV1_SESSION_ID}",
            "SK": "PROGRESS",
            "session_id": LV1_SESSION_ID,
            "lv1_passed": True,
            "lv2_passed": False,
            "lv3_passed": False,
            "lv4_passed": False,
        }
        mock_table = _make_mock_table({
            f"SESSION#{LV3_SESSION_ID}": {},
            f"SESSION#{LV1_SESSION_ID}": lv1_existing,
        })
        mock_ddb = MagicMock()
        mock_ddb.Table.return_value = mock_table

        _update_progress(mock_ddb, LV3_SESSION_ID, True, "2024-01-01T00:00:00+00:00", lv1_session_id=LV1_SESSION_ID)

        lv1_put_calls = [
            c for c in mock_table.put_item.call_args_list
            if c[1]["Item"]["PK"] == f"SESSION#{LV1_SESSION_ID}"
        ]
        lv1_item = lv1_put_calls[0][1]["Item"]
        assert lv1_item["lv1_passed"] is True
        assert lv1_item["lv2_passed"] is False
        assert lv1_item["lv4_passed"] is False
        assert lv1_item["lv3_passed"] is True
