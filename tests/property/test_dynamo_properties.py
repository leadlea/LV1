"""
Property tests for DynamoDB record completeness.

Feature: sojitz-ai-skill-check
Property 7: DynamoDB保存レコードの完全性
"""

import json
import uuid
from unittest.mock import patch, MagicMock

from hypothesis import given, settings, strategies as st

from backend.handlers.selfcheck_handler import handler
from backend.lib.score_calculator import COMMON_IDS, BUSINESS_IDS, ENGINEER_IDS

track_st = st.sampled_from(["business", "engineer"])
score_val = st.integers(min_value=0, max_value=4)
six_scores = st.lists(score_val, min_size=6, max_size=6)


def _build_answers(track, common_vals, track_vals):
    answers = {}
    for i, cid in enumerate(COMMON_IDS):
        answers[cid] = common_vals[i]
    track_ids = BUSINESS_IDS if track == "business" else ENGINEER_IDS
    for i, tid in enumerate(track_ids):
        answers[tid] = track_vals[i]
    return answers


@settings(max_examples=100)
@given(track=track_st, common_vals=six_scores, track_vals=six_scores)
def test_dynamo_record_completeness(track, common_vals, track_vals):
    """Feature: sojitz-ai-skill-check, Property 7: DynamoDB保存レコードの完全性"""
    answers = _build_answers(track, common_vals, track_vals)
    session_id = str(uuid.uuid4())

    event = {"body": json.dumps({
        "session_id": session_id,
        "track": track,
        "answers": answers,
    })}

    mock_table = MagicMock()
    with patch("backend.handlers.selfcheck_handler.boto3") as mock_boto3, \
         patch("backend.handlers.selfcheck_handler.generate_feedback", return_value=None):
        mock_boto3.resource.return_value.Table.return_value = mock_table
        resp = handler(event, None)

    assert resp["statusCode"] == 200
    assert mock_table.put_item.called

    item = mock_table.put_item.call_args[1]["Item"]
    assert item["PK"] == f"SESSION#{session_id}"
    assert item["SK"] == "RESULT#selfcheck"
    for field in ("session_id", "track", "answers", "common_avg", "track_avg",
                  "overall_avg", "skill_level", "feedback", "user_id", "completed_at"):
        assert field in item
