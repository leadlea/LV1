"""PBT-preservation: LV2 complete _update_progress existing progress preservation test.

Feature: lv3-unlock-bug
Property 2: 保持 - 既存プログレスの保全

For any LV2 complete request, the existing lv1_passed, lv3_passed, lv4_passed values
in the LV1 session ID's progress record should not be overwritten by the fixed
_update_progress function.

**Validates: Requirements 3.3, 3.5**
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
# Property test — Property 2: existing progress preservation
# ---------------------------------------------------------------------------

@given(
    lv2_session_id=_uuid_v4_strategy(),
    lv1_session_id=_uuid_v4_strategy(),
    existing_lv1_passed=st.booleans(),
    existing_lv2_passed=st.booleans(),
    existing_lv3_passed=st.booleans(),
    existing_lv4_passed=st.booleans(),
    final_passed=st.booleans(),
    updated_at=_timestamp_strategy(),
)
@settings(max_examples=200)
def test_update_progress_preserves_existing_lv1_progress(
    lv2_session_id,
    lv1_session_id,
    existing_lv1_passed,
    existing_lv2_passed,
    existing_lv3_passed,
    existing_lv4_passed,
    final_passed,
    updated_at,
):
    """Property 2: For any LV2 complete request, the existing lv1_passed, lv3_passed,
    lv4_passed values in the LV1 session ID's progress record are preserved.
    Only lv2_passed is updated to match final_passed.

    **Validates: Requirements 3.3, 3.5**
    """
    assume(lv2_session_id != lv1_session_id)

    # Set up existing LV1 progress record with random values
    lv1_pk = f"SESSION#{lv1_session_id}"
    existing_lv1_record = {
        "PK": lv1_pk,
        "SK": "PROGRESS",
        "session_id": lv1_session_id,
        "lv1_passed": existing_lv1_passed,
        "lv2_passed": existing_lv2_passed,
        "lv3_passed": existing_lv3_passed,
        "lv4_passed": existing_lv4_passed,
        "updated_at": "2024-01-01T00:00:00+00:00",
    }

    mock_table = _make_mock_table({lv1_pk: existing_lv1_record})
    mock_ddb = MagicMock()
    mock_ddb.Table.return_value = mock_table

    _update_progress(mock_ddb, lv2_session_id, final_passed, updated_at, lv1_session_id=lv1_session_id)

    # Find the put_item call for the LV1 session
    lv1_put_calls = [
        c for c in mock_table.put_item.call_args_list
        if c[1]["Item"]["PK"] == lv1_pk
    ]

    assert len(lv1_put_calls) == 1, (
        f"Expected exactly 1 put_item call for LV1 session {lv1_session_id}, "
        f"got {len(lv1_put_calls)}"
    )

    lv1_item = lv1_put_calls[0][1]["Item"]

    # lv1_passed must be preserved (unchanged from existing value)
    assert lv1_item["lv1_passed"] is existing_lv1_passed, (
        f"lv1_passed was overwritten: expected {existing_lv1_passed}, got {lv1_item['lv1_passed']}"
    )

    # lv3_passed must be preserved (unchanged from existing value)
    assert lv1_item["lv3_passed"] is existing_lv3_passed, (
        f"lv3_passed was overwritten: expected {existing_lv3_passed}, got {lv1_item['lv3_passed']}"
    )

    # lv4_passed must be preserved (unchanged from existing value)
    assert lv1_item["lv4_passed"] is existing_lv4_passed, (
        f"lv4_passed was overwritten: expected {existing_lv4_passed}, got {lv1_item['lv4_passed']}"
    )

    # Only lv2_passed should be updated to match final_passed
    assert lv1_item["lv2_passed"] is final_passed, (
        f"lv2_passed was not updated: expected {final_passed}, got {lv1_item['lv2_passed']}"
    )
