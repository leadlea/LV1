"""PBT-exploration: LV2 complete _update_progress bug condition exploration test.

Feature: lv3-unlock-bug
Property 1: 障害条件 - LV2合格時のLV1プログレス更新

For any LV2 complete request where final_passed is true and lv1_session_id is a
valid UUID v4, the fixed _update_progress function should update lv2_passed to true
in the LV1 session ID's progress record.

Since the code has already been fixed, this test validates that the fix works correctly.

**Validates: Requirements 2.1, 2.2**
"""

from unittest.mock import MagicMock

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from backend.handlers.lv2_complete_handler import _update_progress


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
# Exploration test — Property 1: fix condition verification
# ---------------------------------------------------------------------------

@given(
    lv2_session_id=_uuid_v4_strategy(),
    lv1_session_id=_uuid_v4_strategy(),
    final_passed=st.booleans(),
    updated_at=_timestamp_strategy(),
)
@settings(max_examples=200)
def test_fixed_update_progress_sets_lv2_passed_on_lv1_record(
    lv2_session_id, lv1_session_id, final_passed, updated_at
):
    """Property 1: When lv1_session_id is a valid UUID v4, the fixed _update_progress
    updates the LV1 session's progress record with lv2_passed matching final_passed.

    When final_passed=True, lv2_passed should be True in the LV1 progress record.
    When final_passed=False, lv2_passed should be False in the LV1 progress record.

    **Validates: Requirements 2.1, 2.2**
    """
    # Ensure distinct session IDs (LV2 and LV1 are always different in practice)
    assume(lv2_session_id != lv1_session_id)

    mock_table = _make_mock_table({})
    mock_ddb = MagicMock()
    mock_ddb.Table.return_value = mock_table

    _update_progress(mock_ddb, lv2_session_id, final_passed, updated_at, lv1_session_id=lv1_session_id)

    # Find the put_item call for the LV1 session
    lv1_put_calls = [
        c for c in mock_table.put_item.call_args_list
        if c[1]["Item"]["PK"] == f"SESSION#{lv1_session_id}"
    ]

    # LV1 progress record must exist
    assert len(lv1_put_calls) == 1, (
        f"Expected exactly 1 put_item call for LV1 session {lv1_session_id}, "
        f"got {len(lv1_put_calls)}"
    )

    lv1_item = lv1_put_calls[0][1]["Item"]

    # lv2_passed must match final_passed
    assert lv1_item["lv2_passed"] is final_passed, (
        f"Expected lv2_passed={final_passed} in LV1 progress, got {lv1_item['lv2_passed']}"
    )

    # session_id in the record should be the LV1 session ID
    assert lv1_item["session_id"] == lv1_session_id
