"""
Property tests for score calculation and level determination.

Feature: sojitz-ai-skill-check
Property 1: スコア集計の数学的正当性
Property 2: レベル判定の正当性
Property 4: スコアバリデーションの正当性
"""

import math
from hypothesis import given, settings, strategies as st

from backend.lib.score_calculator import (
    calculate_scores,
    determine_level,
    validate_answers,
    COMMON_IDS,
    BUSINESS_IDS,
    ENGINEER_IDS,
)


def _build_answers(track, common_vals, track_vals):
    """Helper to build a valid answers dict."""
    answers = {}
    for i, cid in enumerate(COMMON_IDS):
        answers[cid] = common_vals[i]
    track_ids = BUSINESS_IDS if track == "business" else ENGINEER_IDS
    for i, tid in enumerate(track_ids):
        answers[tid] = track_vals[i]
    return answers


score_value = st.integers(min_value=0, max_value=4)
six_scores = st.lists(score_value, min_size=6, max_size=6)
track_st = st.sampled_from(["business", "engineer"])


# --- Property 1: スコア集計の数学的正当性 ---

@settings(max_examples=200)
@given(track=track_st, common_vals=six_scores, track_vals=six_scores)
def test_score_arithmetic_correctness(track, common_vals, track_vals):
    """Feature: sojitz-ai-skill-check, Property 1: スコア集計の数学的正当性"""
    answers = _build_answers(track, common_vals, track_vals)
    result = calculate_scores(track, answers)

    expected_common = sum(common_vals) / 6
    expected_track = sum(track_vals) / 6
    expected_overall = (expected_common + expected_track) / 2

    assert math.isclose(result["common_avg"], expected_common, abs_tol=1e-3)
    assert math.isclose(result["track_avg"], expected_track, abs_tol=1e-3)
    assert math.isclose(result["overall_avg"], expected_overall, abs_tol=1e-3)


# --- Property 2: レベル判定の正当性 ---

@settings(max_examples=200)
@given(avg=st.floats(min_value=0.0, max_value=4.0, allow_nan=False))
def test_level_determination_correctness(avg):
    """Feature: sojitz-ai-skill-check, Property 2: レベル判定の正当性"""
    level = determine_level(avg)
    if avg < 1.0:
        assert level == "Lv1"
    elif avg < 2.0:
        assert level == "Lv2"
    elif avg < 3.0:
        assert level == "Lv3"
    elif avg < 3.5:
        assert level == "Lv4"
    else:
        assert level == "Lv5"


# --- Property 4: スコアバリデーションの正当性 ---

@settings(max_examples=200)
@given(track=track_st, bad_value=st.one_of(
    st.integers(max_value=-1),
    st.integers(min_value=5),
    st.floats(min_value=0.0, max_value=4.0).filter(lambda x: x != int(x)),
    st.text(min_size=1, max_size=5),
))
def test_invalid_answer_values_rejected(track, bad_value):
    """Feature: sojitz-ai-skill-check, Property 4: スコアバリデーションの正当性"""
    # Build valid answers then corrupt one
    answers = _build_answers(track, [2] * 6, [2] * 6)
    first_key = list(answers.keys())[0]
    answers[first_key] = bad_value
    error = validate_answers(track, answers)
    assert error is not None
