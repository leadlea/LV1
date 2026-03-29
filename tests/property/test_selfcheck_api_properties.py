"""
Property tests for selfcheck API handler.

Feature: sojitz-ai-skill-check
Property 5: session_idバリデーションの正当性
Property 8: APIレスポンス構造の正当性
Property 9: CORSヘッダーの付与
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

# UUID v4 regex for filtering
UUID4_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"


def _build_answers(track, common_vals, track_vals):
    answers = {}
    for i, cid in enumerate(COMMON_IDS):
        answers[cid] = common_vals[i]
    track_ids = BUSINESS_IDS if track == "business" else ENGINEER_IDS
    for i, tid in enumerate(track_ids):
        answers[tid] = track_vals[i]
    return answers


def _make_event(body_dict):
    return {"body": json.dumps(body_dict)}


# --- Property 5: session_idバリデーションの正当性 ---

@settings(max_examples=200)
@given(bad_id=st.text(min_size=0, max_size=50).filter(
    lambda s: not __import__("re").match(UUID4_PATTERN, s, __import__("re").IGNORECASE)
))
def test_invalid_session_id_returns_400(bad_id):
    """Feature: sojitz-ai-skill-check, Property 5: session_idバリデーションの正当性"""
    event = _make_event({
        "session_id": bad_id,
        "track": "business",
        "answers": {},
    })
    resp = handler(event, None)
    assert resp["statusCode"] == 400
    body = json.loads(resp["body"])
    assert "session_id" in body["error"]


# --- Property 8: APIレスポンス構造の正当性 ---

@settings(max_examples=100)
@given(track=track_st, common_vals=six_scores, track_vals=six_scores)
def test_api_response_structure(track, common_vals, track_vals):
    """Feature: sojitz-ai-skill-check, Property 8: APIレスポンス構造の正当性"""
    answers = _build_answers(track, common_vals, track_vals)
    session_id = str(uuid.uuid4())

    event = _make_event({
        "session_id": session_id,
        "track": track,
        "answers": answers,
    })

    mock_table = MagicMock()
    with patch("backend.handlers.selfcheck_handler.boto3") as mock_boto3, \
         patch("backend.handlers.selfcheck_handler.generate_feedback", return_value=None):
        mock_boto3.resource.return_value.Table.return_value = mock_table
        resp = handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    for key in ("session_id", "track", "common_avg", "track_avg", "overall_avg", "skill_level", "feedback"):
        assert key in body


# --- Property 9: CORSヘッダーの付与 ---

@settings(max_examples=100)
@given(track=track_st, common_vals=six_scores, track_vals=six_scores)
def test_cors_headers_present(track, common_vals, track_vals):
    """Feature: sojitz-ai-skill-check, Property 9: CORSヘッダーの付与"""
    answers = _build_answers(track, common_vals, track_vals)
    session_id = str(uuid.uuid4())

    event = _make_event({
        "session_id": session_id,
        "track": track,
        "answers": answers,
    })

    mock_table = MagicMock()
    with patch("backend.handlers.selfcheck_handler.boto3") as mock_boto3, \
         patch("backend.handlers.selfcheck_handler.generate_feedback", return_value=None):
        mock_boto3.resource.return_value.Table.return_value = mock_table
        resp = handler(event, None)

    assert resp["headers"]["Access-Control-Allow-Origin"] == "*"


def test_cors_headers_on_error():
    """CORSヘッダーはエラーレスポンスにも付与される"""
    event = _make_event({"session_id": "invalid", "track": "business", "answers": {}})
    resp = handler(event, None)
    assert resp["statusCode"] == 400
    assert resp["headers"]["Access-Control-Allow-Origin"] == "*"
