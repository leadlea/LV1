"""Unit tests for backend/handlers/lv2_complete_handler.py - LV1 progress update logic"""

import json
from unittest.mock import patch, MagicMock, call

import pytest

from backend.handlers.lv2_complete_handler import handler, _update_progress, _validate_body


LV2_SESSION_ID = "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
LV1_SESSION_ID = "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e"


def _api_event(body: dict) -> dict:
    return {"body": json.dumps(body)}


VALID_BODY = {
    "session_id": LV2_SESSION_ID,
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
    """Task 3.1: LV1セッションIDのプログレスが正しく更新されるテスト"""

    def test_lv1_progress_lv2_passed_set_true_when_final_passed(self):
        """When final_passed=True and lv1_session_id is provided, LV1 progress should have lv2_passed=True."""
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
            f"SESSION#{LV2_SESSION_ID}": {},
            f"SESSION#{LV1_SESSION_ID}": lv1_existing,
        })
        mock_ddb = MagicMock()
        mock_ddb.Table.return_value = mock_table

        _update_progress(mock_ddb, LV2_SESSION_ID, True, "2024-01-01T00:00:00+00:00", lv1_session_id=LV1_SESSION_ID)

        # Find the put_item call for LV1 session
        lv1_put_calls = [
            c for c in mock_table.put_item.call_args_list
            if c[1]["Item"]["PK"] == f"SESSION#{LV1_SESSION_ID}"
            or (c[0] and c[0][0].get("Item", {}).get("PK") == f"SESSION#{LV1_SESSION_ID}")
        ]
        assert len(lv1_put_calls) == 1
        lv1_item = lv1_put_calls[0][1]["Item"]
        assert lv1_item["lv2_passed"] is True

    def test_lv2_progress_also_updated(self):
        """LV2 session's own progress should still be updated."""
        mock_table = _make_mock_table({})
        mock_ddb = MagicMock()
        mock_ddb.Table.return_value = mock_table

        _update_progress(mock_ddb, LV2_SESSION_ID, True, "2024-01-01T00:00:00+00:00", lv1_session_id=LV1_SESSION_ID)

        # Should have 2 put_item calls: one for LV2 session, one for LV1 session
        assert mock_table.put_item.call_count == 2

        lv2_put_calls = [
            c for c in mock_table.put_item.call_args_list
            if c[1]["Item"]["PK"] == f"SESSION#{LV2_SESSION_ID}"
        ]
        assert len(lv2_put_calls) == 1
        assert lv2_put_calls[0][1]["Item"]["lv2_passed"] is True

    @patch("backend.handlers.lv2_complete_handler._get_dynamodb_resource")
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


class TestFallbackWithoutLv1SessionId:
    """Task 3.2: lv1_session_id が欠落している場合のフォールバック動作テスト"""

    def test_no_lv1_session_id_only_updates_lv2_progress(self):
        """When lv1_session_id is None, only LV2 session progress is updated."""
        mock_table = _make_mock_table({})
        mock_ddb = MagicMock()
        mock_ddb.Table.return_value = mock_table

        _update_progress(mock_ddb, LV2_SESSION_ID, True, "2024-01-01T00:00:00+00:00", lv1_session_id=None)

        # Only 1 put_item call (LV2 session only)
        assert mock_table.put_item.call_count == 1
        item = mock_table.put_item.call_args_list[0][1]["Item"]
        assert item["PK"] == f"SESSION#{LV2_SESSION_ID}"
        assert item["lv2_passed"] is True

    def test_default_parameter_omits_lv1_update(self):
        """When lv1_session_id is not passed at all, only LV2 session progress is updated."""
        mock_table = _make_mock_table({})
        mock_ddb = MagicMock()
        mock_ddb.Table.return_value = mock_table

        _update_progress(mock_ddb, LV2_SESSION_ID, True, "2024-01-01T00:00:00+00:00")

        assert mock_table.put_item.call_count == 1

    @patch("backend.handlers.lv2_complete_handler._get_dynamodb_resource")
    def test_handler_without_lv1_session_id_in_body(self, mock_ddb):
        """Handler should work when lv1_session_id is not in the request body."""
        mock_table = _make_mock_table({})
        mock_ddb.return_value.Table.return_value = mock_table

        body_without_lv1 = {**VALID_BODY}
        del body_without_lv1["lv1_session_id"]

        resp = handler(_api_event(body_without_lv1), None)

        assert resp["statusCode"] == 200
        # Only LV2 progress + result = 2 put_item calls (1 result + 1 progress)
        lv1_put_calls = [
            c for c in mock_table.put_item.call_args_list
            if c[1]["Item"].get("PK") == f"SESSION#{LV1_SESSION_ID}"
        ]
        assert len(lv1_put_calls) == 0


class TestFinalPassedFalse:
    """Task 3.3: final_passed: false の場合に lv2_passed が true にならないテスト"""

    def test_lv1_progress_lv2_passed_false_when_not_passed(self):
        """When final_passed=False, LV1 progress should have lv2_passed=False."""
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
            f"SESSION#{LV2_SESSION_ID}": {},
            f"SESSION#{LV1_SESSION_ID}": lv1_existing,
        })
        mock_ddb = MagicMock()
        mock_ddb.Table.return_value = mock_table

        _update_progress(mock_ddb, LV2_SESSION_ID, False, "2024-01-01T00:00:00+00:00", lv1_session_id=LV1_SESSION_ID)

        lv1_put_calls = [
            c for c in mock_table.put_item.call_args_list
            if c[1]["Item"]["PK"] == f"SESSION#{LV1_SESSION_ID}"
        ]
        assert len(lv1_put_calls) == 1
        assert lv1_put_calls[0][1]["Item"]["lv2_passed"] is False

    def test_lv2_progress_also_false_when_not_passed(self):
        """LV2 session progress should also have lv2_passed=False."""
        mock_table = _make_mock_table({})
        mock_ddb = MagicMock()
        mock_ddb.Table.return_value = mock_table

        _update_progress(mock_ddb, LV2_SESSION_ID, False, "2024-01-01T00:00:00+00:00", lv1_session_id=LV1_SESSION_ID)

        lv2_put_calls = [
            c for c in mock_table.put_item.call_args_list
            if c[1]["Item"]["PK"] == f"SESSION#{LV2_SESSION_ID}"
        ]
        assert len(lv2_put_calls) == 1
        assert lv2_put_calls[0][1]["Item"]["lv2_passed"] is False


class TestExistingProgressPreservation:
    """Task 3.4: 既存プログレス（lv1_passed、lv3_passed、lv4_passed）が上書きされないテスト"""

    def test_lv1_passed_preserved_in_lv1_progress(self):
        """Existing lv1_passed=True in LV1 progress should not be overwritten."""
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
            f"SESSION#{LV2_SESSION_ID}": {},
            f"SESSION#{LV1_SESSION_ID}": lv1_existing,
        })
        mock_ddb = MagicMock()
        mock_ddb.Table.return_value = mock_table

        _update_progress(mock_ddb, LV2_SESSION_ID, True, "2024-01-01T00:00:00+00:00", lv1_session_id=LV1_SESSION_ID)

        lv1_put_calls = [
            c for c in mock_table.put_item.call_args_list
            if c[1]["Item"]["PK"] == f"SESSION#{LV1_SESSION_ID}"
        ]
        lv1_item = lv1_put_calls[0][1]["Item"]
        assert lv1_item["lv1_passed"] is True

    def test_lv3_passed_preserved_in_lv1_progress(self):
        """Existing lv3_passed=True in LV1 progress should not be overwritten."""
        lv1_existing = {
            "PK": f"SESSION#{LV1_SESSION_ID}",
            "SK": "PROGRESS",
            "session_id": LV1_SESSION_ID,
            "lv1_passed": True,
            "lv2_passed": True,
            "lv3_passed": True,
            "lv4_passed": False,
        }
        mock_table = _make_mock_table({
            f"SESSION#{LV2_SESSION_ID}": {},
            f"SESSION#{LV1_SESSION_ID}": lv1_existing,
        })
        mock_ddb = MagicMock()
        mock_ddb.Table.return_value = mock_table

        _update_progress(mock_ddb, LV2_SESSION_ID, True, "2024-01-01T00:00:00+00:00", lv1_session_id=LV1_SESSION_ID)

        lv1_put_calls = [
            c for c in mock_table.put_item.call_args_list
            if c[1]["Item"]["PK"] == f"SESSION#{LV1_SESSION_ID}"
        ]
        lv1_item = lv1_put_calls[0][1]["Item"]
        assert lv1_item["lv3_passed"] is True

    def test_lv4_passed_preserved_in_lv1_progress(self):
        """Existing lv4_passed=True in LV1 progress should not be overwritten."""
        lv1_existing = {
            "PK": f"SESSION#{LV1_SESSION_ID}",
            "SK": "PROGRESS",
            "session_id": LV1_SESSION_ID,
            "lv1_passed": True,
            "lv2_passed": True,
            "lv3_passed": True,
            "lv4_passed": True,
        }
        mock_table = _make_mock_table({
            f"SESSION#{LV2_SESSION_ID}": {},
            f"SESSION#{LV1_SESSION_ID}": lv1_existing,
        })
        mock_ddb = MagicMock()
        mock_ddb.Table.return_value = mock_table

        _update_progress(mock_ddb, LV2_SESSION_ID, True, "2024-01-01T00:00:00+00:00", lv1_session_id=LV1_SESSION_ID)

        lv1_put_calls = [
            c for c in mock_table.put_item.call_args_list
            if c[1]["Item"]["PK"] == f"SESSION#{LV1_SESSION_ID}"
        ]
        lv1_item = lv1_put_calls[0][1]["Item"]
        assert lv1_item["lv4_passed"] is True

    def test_all_existing_progress_preserved_together(self):
        """All existing progress values should be preserved when updating lv2_passed."""
        lv1_existing = {
            "PK": f"SESSION#{LV1_SESSION_ID}",
            "SK": "PROGRESS",
            "session_id": LV1_SESSION_ID,
            "lv1_passed": True,
            "lv2_passed": False,
            "lv3_passed": True,
            "lv4_passed": True,
        }
        mock_table = _make_mock_table({
            f"SESSION#{LV2_SESSION_ID}": {},
            f"SESSION#{LV1_SESSION_ID}": lv1_existing,
        })
        mock_ddb = MagicMock()
        mock_ddb.Table.return_value = mock_table

        _update_progress(mock_ddb, LV2_SESSION_ID, True, "2024-01-01T00:00:00+00:00", lv1_session_id=LV1_SESSION_ID)

        lv1_put_calls = [
            c for c in mock_table.put_item.call_args_list
            if c[1]["Item"]["PK"] == f"SESSION#{LV1_SESSION_ID}"
        ]
        lv1_item = lv1_put_calls[0][1]["Item"]
        assert lv1_item["lv1_passed"] is True
        assert lv1_item["lv2_passed"] is True
        assert lv1_item["lv3_passed"] is True
        assert lv1_item["lv4_passed"] is True
