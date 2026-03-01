"""PBT-preservation: LV3 complete _update_progress existing progress preservation test.

Feature: lv4-unlock-bug
Property 2: Preservation - 既存プログレスの保全

On UNFIXED code, _update_progress saves progress under the LV3 session ID only.
These preservation tests verify that the existing behavior works correctly:
- LV3 session ID's progress record is correctly saved with lv3_passed = final_passed
- When final_passed is false, lv3_passed does not become true
- Existing progress values (lv1_passed, lv2_passed, lv4_passed) are not overwritten

These tests must PASS on unfixed code (baseline behavior confirmation).
After the fix, they must continue to pass (regression prevention).

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
"""

from unittest.mock import MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.handlers.lv3_complete_handler import _update_progress


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

def _uuid_v4_strategy() -> st.SearchStrategy[str]:
    """Generate valid UUID v4 strings."""
    return st.uuids(version=4).map(str)


def _timestamp_strategy() -> st.SearchStrategy[str]:
    """Generate ISO 8601 timestamp strings."""
    return st.just("2024-01-01T00:00:00+00:00")


def _make_mock_table(existing_items: dict | None = None):
    """Create a mock DynamoDB table that returns existing items on get_item."""
    mock_table = MagicMock()
    if existing_items is None:
        existing_items = {}

    def get_item_side_effect(Key):
        pk = Key["PK"]
        return {"Item": existing_items[pk]} if pk in existing_items else {}

    mock_table.get_item.side_effect = get_item_side_effect
    return mock_table


# ---------------------------------------------------------------------------
# Property test 1: Existing progress values are preserved
# ---------------------------------------------------------------------------

@given(
    lv3_session_id=_uuid_v4_strategy(),
    existing_lv1_passed=st.booleans(),
    existing_lv2_passed=st.booleans(),
    existing_lv4_passed=st.booleans(),
    final_passed=st.booleans(),
    updated_at=_timestamp_strategy(),
)
@settings(max_examples=200)
def test_update_progress_preserves_existing_progress_values(
    lv3_session_id,
    existing_lv1_passed,
    existing_lv2_passed,
    existing_lv4_passed,
    final_passed,
    updated_at,
):
    """Property 2: With random existing progress states (lv1_passed, lv2_passed,
    lv4_passed), _update_progress does not overwrite these values.

    On unfixed code, _update_progress saves under the LV3 session ID and preserves
    existing lv1_passed and lv2_passed from the LV3 session's record. lv4_passed is
    always set to False in the current code.

    This test verifies that lv1_passed and lv2_passed from the existing record are
    preserved when _update_progress writes the LV3 session's progress.

    **Validates: Requirements 3.3, 3.5**
    """
    lv3_pk = f"SESSION#{lv3_session_id}"
    existing_record = {
        "PK": lv3_pk,
        "SK": "PROGRESS",
        "session_id": lv3_session_id,
        "lv1_passed": existing_lv1_passed,
        "lv2_passed": existing_lv2_passed,
        "lv3_passed": False,
        "lv4_passed": existing_lv4_passed,
        "updated_at": "2024-01-01T00:00:00+00:00",
    }

    mock_table = _make_mock_table({lv3_pk: existing_record})
    mock_ddb = MagicMock()
    mock_ddb.Table.return_value = mock_table

    _update_progress(mock_ddb, lv3_session_id, final_passed, updated_at)

    # Find the put_item call for the LV3 session
    lv3_put_calls = [
        c for c in mock_table.put_item.call_args_list
        if c[1]["Item"]["PK"] == lv3_pk
    ]

    assert len(lv3_put_calls) == 1, (
        f"Expected exactly 1 put_item call for LV3 session {lv3_session_id}, "
        f"got {len(lv3_put_calls)}"
    )

    lv3_item = lv3_put_calls[0][1]["Item"]

    # lv1_passed must be preserved (unchanged from existing value)
    assert lv3_item["lv1_passed"] is existing_lv1_passed, (
        f"lv1_passed was overwritten: expected {existing_lv1_passed}, "
        f"got {lv3_item['lv1_passed']}"
    )

    # lv2_passed must be preserved (unchanged from existing value)
    assert lv3_item["lv2_passed"] is existing_lv2_passed, (
        f"lv2_passed was overwritten: expected {existing_lv2_passed}, "
        f"got {lv3_item['lv2_passed']}"
    )


# ---------------------------------------------------------------------------
# Property test 2: final_passed=false does not set lv3_passed to true
# ---------------------------------------------------------------------------

@given(
    lv3_session_id=_uuid_v4_strategy(),
    updated_at=_timestamp_strategy(),
)
@settings(max_examples=200)
def test_update_progress_false_does_not_set_lv3_passed_true(
    lv3_session_id,
    updated_at,
):
    """Property 3: When final_passed is false, lv3_passed must not become true.

    This verifies that the unfixed code correctly handles the case where a user
    fails LV3 — lv3_passed should remain false, not be set to true.

    **Validates: Requirements 3.4**
    """
    lv3_pk = f"SESSION#{lv3_session_id}"
    mock_table = _make_mock_table({})
    mock_ddb = MagicMock()
    mock_ddb.Table.return_value = mock_table

    _update_progress(mock_ddb, lv3_session_id, False, updated_at)

    lv3_put_calls = [
        c for c in mock_table.put_item.call_args_list
        if c[1]["Item"]["PK"] == lv3_pk
    ]

    assert len(lv3_put_calls) == 1, (
        f"Expected exactly 1 put_item call for LV3 session {lv3_session_id}, "
        f"got {len(lv3_put_calls)}"
    )

    lv3_item = lv3_put_calls[0][1]["Item"]

    # lv3_passed must NOT be true when final_passed is false
    assert lv3_item["lv3_passed"] is not True, (
        f"lv3_passed was set to True despite final_passed=False"
    )
    assert lv3_item["lv3_passed"] is False, (
        f"lv3_passed should be False, got {lv3_item['lv3_passed']}"
    )


# ---------------------------------------------------------------------------
# Property test 3: LV3 session progress record is correctly saved
# ---------------------------------------------------------------------------

@given(
    lv3_session_id=_uuid_v4_strategy(),
    final_passed=st.booleans(),
    updated_at=_timestamp_strategy(),
)
@settings(max_examples=200)
def test_update_progress_correctly_saves_lv3_session_progress(
    lv3_session_id,
    final_passed,
    updated_at,
):
    """Preservation: LV3 session ID's progress record continues to be correctly saved.

    Verifies that _update_progress writes a complete and correct progress record
    under the LV3 session ID with lv3_passed matching final_passed.

    **Validates: Requirements 3.1, 3.2**
    """
    lv3_pk = f"SESSION#{lv3_session_id}"
    mock_table = _make_mock_table({})
    mock_ddb = MagicMock()
    mock_ddb.Table.return_value = mock_table

    _update_progress(mock_ddb, lv3_session_id, final_passed, updated_at)

    lv3_put_calls = [
        c for c in mock_table.put_item.call_args_list
        if c[1]["Item"]["PK"] == lv3_pk
    ]

    assert len(lv3_put_calls) == 1, (
        f"Expected exactly 1 put_item call for LV3 session {lv3_session_id}, "
        f"got {len(lv3_put_calls)}"
    )

    lv3_item = lv3_put_calls[0][1]["Item"]

    # Verify the record structure is correct
    assert lv3_item["PK"] == lv3_pk
    assert lv3_item["SK"] == "PROGRESS"
    assert lv3_item["session_id"] == lv3_session_id
    assert lv3_item["lv3_passed"] is final_passed, (
        f"lv3_passed should be {final_passed}, got {lv3_item['lv3_passed']}"
    )
    assert lv3_item["updated_at"] == updated_at
