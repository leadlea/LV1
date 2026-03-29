"""
Property tests for feedback structure.

Feature: sojitz-ai-skill-check
Property 6: フィードバック構造の正当性
"""

import json
from unittest.mock import patch

from hypothesis import given, settings, strategies as st

from backend.lib.feedback_generator import generate_feedback
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


def _mock_bedrock_response(strengths="強み", improvements="改善", next_actions="アクション"):
    feedback_json = json.dumps({
        "strengths": strengths,
        "improvements": improvements,
        "next_actions": next_actions,
    }, ensure_ascii=False)
    return {
        "content": [{"text": feedback_json}],
    }


@settings(max_examples=100)
@given(track=track_st, common_vals=six_scores, track_vals=six_scores)
def test_feedback_structure_correctness(track, common_vals, track_vals):
    """Feature: sojitz-ai-skill-check, Property 6: フィードバック構造の正当性"""
    answers = _build_answers(track, common_vals, track_vals)
    scores = {
        "common_avg": sum(common_vals) / 6,
        "track_avg": sum(track_vals) / 6,
        "overall_avg": (sum(common_vals) / 6 + sum(track_vals) / 6) / 2,
        "skill_level": "Lv3",
    }

    with patch("backend.lib.feedback_generator.invoke_claude") as mock_claude:
        mock_claude.return_value = _mock_bedrock_response()
        result = generate_feedback(track, answers, scores)

    assert result is not None
    assert "strengths" in result and result["strengths"]
    assert "improvements" in result and result["improvements"]
    assert "next_actions" in result and result["next_actions"]
