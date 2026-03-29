"""ユニットテスト: スコア集計・レベル判定"""

import pytest
from backend.lib.score_calculator import validate_answers, calculate_scores, determine_level


def _make_answers(track, common_val=2, track_val=2):
    """全項目を同一値で埋めたanswersを生成"""
    answers = {f"common_{i}": common_val for i in range(1, 7)}
    prefix = "biz" if track == "business" else "eng"
    for i in range(1, 7):
        answers[f"{prefix}_{i}"] = track_val
    return answers


class TestCalculateScores:
    def test_all_zeros(self):
        answers = _make_answers("business", 0, 0)
        result = calculate_scores("business", answers)
        assert result["common_avg"] == 0.0
        assert result["track_avg"] == 0.0
        assert result["overall_avg"] == 0.0
        assert result["skill_level"] == "Lv1"

    def test_all_fours(self):
        answers = _make_answers("engineer", 4, 4)
        result = calculate_scores("engineer", answers)
        assert result["common_avg"] == 4.0
        assert result["track_avg"] == 4.0
        assert result["overall_avg"] == 4.0
        assert result["skill_level"] == "Lv5"

    def test_mixed_scores(self):
        answers = _make_answers("business", 2, 3)
        result = calculate_scores("business", answers)
        assert result["common_avg"] == 2.0
        assert result["track_avg"] == 3.0
        assert result["overall_avg"] == 2.5
        assert result["skill_level"] == "Lv3"


class TestDetermineLevel:
    @pytest.mark.parametrize("avg,expected", [
        (0.0, "Lv1"), (0.5, "Lv1"), (0.99, "Lv1"),
        (1.0, "Lv2"), (1.5, "Lv2"), (1.99, "Lv2"),
        (2.0, "Lv3"), (2.5, "Lv3"), (2.99, "Lv3"),
        (3.0, "Lv4"), (3.25, "Lv4"), (3.49, "Lv4"),
        (3.5, "Lv5"), (3.75, "Lv5"), (4.0, "Lv5"),
    ])
    def test_boundary_values(self, avg, expected):
        assert determine_level(avg) == expected


class TestValidateAnswers:
    def test_valid_business(self):
        answers = _make_answers("business")
        assert validate_answers("business", answers) is None

    def test_valid_engineer(self):
        answers = _make_answers("engineer")
        assert validate_answers("engineer", answers) is None

    def test_invalid_track(self):
        assert validate_answers("invalid", {}) is not None

    def test_out_of_range_high(self):
        answers = _make_answers("business")
        answers["common_1"] = 5
        assert validate_answers("business", answers) is not None

    def test_out_of_range_low(self):
        answers = _make_answers("business")
        answers["common_1"] = -1
        assert validate_answers("business", answers) is not None

    def test_non_integer(self):
        answers = _make_answers("business")
        answers["common_1"] = 2.5
        assert validate_answers("business", answers) is not None

    def test_missing_items(self):
        answers = {f"common_{i}": 2 for i in range(1, 7)}
        # Only 6 items, missing track items
        assert validate_answers("business", answers) is not None

    def test_wrong_track_keys(self):
        answers = _make_answers("business")
        # Use engineer keys for business track
        answers_wrong = _make_answers("engineer")
        assert validate_answers("business", answers_wrong) is not None
