"""Property-based tests for complete_handler.

Feature: ai-levels-lv1-mvp, Property 5: 完了レコードの完全性

Validates: Requirements 5.1, 5.3
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.handlers.complete_handler import handler


def _uuid_v4_strategy():
    """Generate valid UUID v4 strings."""
    hex_chars = "0123456789abcdef"
    return st.tuples(
        st.text(alphabet=hex_chars, min_size=8, max_size=8),
        st.text(alphabet=hex_chars, min_size=4, max_size=4),
        st.text(alphabet=hex_chars, min_size=3, max_size=3),
        st.sampled_from(list("89ab")),
        st.text(alphabet=hex_chars, min_size=3, max_size=3),
        st.text(alphabet=hex_chars, min_size=12, max_size=12),
    ).map(lambda t: f"{t[0]}-{t[1]}-4{t[2]}-{t[3]}{t[4]}-{t[5]}")


def _grade_strategy():
    """Generate a grade dict with passed and score."""
    return st.fixed_dictionaries({
        "passed": st.booleans(),
        "score": st.integers(min_value=0, max_value=100),
    })


@given(
    session_id=_uuid_v4_strategy(),
    questions=st.lists(st.text(min_size=1, max_size=100).filter(lambda s: s.strip()), min_size=1, max_size=5),
    answers=st.lists(st.text(min_size=1, max_size=100).filter(lambda s: s.strip()), min_size=1, max_size=5),
    grades=st.lists(_grade_strategy(), min_size=1, max_size=5),
    final_passed=st.booleans(),
)
@settings(max_examples=100)
def test_complete_record_completeness(session_id, questions, answers, grades, final_passed):
    """Property 5: 完了レコードの完全性

    任意の完了データに対して、DynamoDBに保存されるレコードは、
    session_id、completed_at（ISO 8601タイムスタンプ）、questions、answers、
    grades、final_passedの全フィールドを含むこと。

    **Validates: Requirements 5.1, 5.3**
    """
    event = {
        "body": json.dumps({
            "session_id": session_id,
            "questions": questions,
            "answers": answers,
            "grades": grades,
            "final_passed": final_passed,
        })
    }

    # Capture what gets written to DynamoDB
    results_items = []
    progress_items = []

    mock_results_table = MagicMock()
    mock_results_table.put_item.side_effect = lambda Item: results_items.append(Item)

    mock_progress_table = MagicMock()
    mock_progress_table.put_item.side_effect = lambda Item: progress_items.append(Item)

    mock_dynamodb = MagicMock()
    mock_dynamodb.Table.side_effect = lambda name: (
        mock_results_table if name == "ai-levels-results" else mock_progress_table
    )

    with patch("backend.handlers.complete_handler._get_dynamodb_resource", return_value=mock_dynamodb):
        resp = handler(event, None)

    assert resp["statusCode"] == 200

    # Verify results table record completeness
    assert len(results_items) == 1
    record = results_items[0]

    assert record["session_id"] == session_id
    assert record["questions"] == questions
    assert record["answers"] == answers
    assert record["grades"] == grades
    assert record["final_passed"] == final_passed

    # completed_at must be a valid ISO 8601 timestamp
    assert isinstance(record["completed_at"], str)
    datetime.fromisoformat(record["completed_at"])

    # PK/SK structure
    assert record["PK"] == f"SESSION#{session_id}"
    assert record["SK"] == "RESULT#lv1"

    # Verify progress table record
    assert len(progress_items) == 1
    progress = progress_items[0]
    assert progress["session_id"] == session_id
    assert progress["lv1_passed"] == final_passed
