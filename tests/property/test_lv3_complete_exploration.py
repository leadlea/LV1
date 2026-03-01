"""PBT-exploration: LV3 complete _update_progress bug condition exploration test.

Feature: lv4-unlock-bug
Property 1: Fault Condition - LV3合格時のLV1プログレス未更新

For any LV3 complete request where final_passed is true and lv1_session_id is a
valid UUID v4 (distinct from lv3_session_id), the _update_progress function should
update lv3_passed to true in the LV1 session ID's progress record.

On UNFIXED code, this test is EXPECTED TO FAIL because _update_progress only saves
progress under the LV3 session ID, never updating the LV1 session's record.

**Validates: Requirements 1.1, 2.1**
"""

from unittest.mock import MagicMock

from hypothesis import given, settings, assume
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
# Exploration test — Property 1: Fault Condition
# ---------------------------------------------------------------------------

@given(
    lv3_session_id=_uuid_v4_strategy(),
    lv1_session_id=_uuid_v4_strategy(),
    updated_at=_timestamp_strategy(),
)
@settings(max_examples=200)
def test_update_progress_sets_lv3_passed_on_lv1_record(
    lv3_session_id, lv1_session_id, updated_at
):
    """Property 1: When final_passed=True and lv1_session_id is a valid UUID v4
    distinct from lv3_session_id, _update_progress should update the LV1 session's
    progress record with lv3_passed=True.

    On unfixed code, this FAILS because _update_progress only writes to the LV3
    session's progress record and never touches the LV1 session's record.
    The counterexample: LV1 session ID's progress record's lv3_passed remains false.

    **Validates: Requirements 1.1, 2.1**
    """
    # Scoped: final_passed=True, distinct session IDs
    assume(lv3_session_id != lv1_session_id)

    mock_table = _make_mock_table({})
    mock_ddb = MagicMock()
    mock_ddb.Table.return_value = mock_table

    # Call _update_progress with lv1_session_id to exercise the fixed code path.
    _update_progress(mock_ddb, lv3_session_id, True, updated_at, lv1_session_id=lv1_session_id)

    # Find the put_item call for the LV1 session
    lv1_put_calls = [
        c for c in mock_table.put_item.call_args_list
        if c[1]["Item"]["PK"] == f"SESSION#{lv1_session_id}"
    ]

    # LV1 progress record must exist — this will FAIL on unfixed code
    assert len(lv1_put_calls) == 1, (
        f"Expected exactly 1 put_item call for LV1 session {lv1_session_id}, "
        f"got {len(lv1_put_calls)}. "
        f"Bug: _update_progress only updates LV3 session {lv3_session_id}, "
        f"LV1 session progress is never written."
    )

    lv1_item = lv1_put_calls[0][1]["Item"]

    # lv3_passed must be True in the LV1 progress record
    assert lv1_item["lv3_passed"] is True, (
        f"Expected lv3_passed=True in LV1 progress, got {lv1_item['lv3_passed']}"
    )

    # session_id in the record should be the LV1 session ID
    assert lv1_item["session_id"] == lv1_session_id
