"""
Property tests for history comparison display logic.

Feature: aoki-feedback-improvements
Property 1: 前回比較の差分計算正当性
Property 2: 差分フォーマットの符号・値正当性
Property 3: レベル変化フォーマットの正当性

フロントエンドJSの比較ロジックをPythonで再実装してhypothesisでテスト
"""

import math
import re

from hypothesis import given, settings, strategies as st


# ---- Python re-implementation of frontend JS comparison logic ----

def format_diff(current_str, previous_str):
    """Re-implementation of formatDiff() from history.html"""
    try:
        cur = float(current_str)
        prev = float(previous_str)
    except (ValueError, TypeError):
        return {"text": "-", "color": None}

    if math.isnan(cur) or math.isnan(prev):
        return {"text": "-", "color": None}

    diff = cur - prev

    if diff > 0:
        return {"text": f"+{diff:.2f}", "color": "--green"}
    elif diff < 0:
        return {"text": f"{diff:.2f}", "color": "--error"}
    else:
        return {"text": "±0.00", "color": "--text-light"}


def format_level_change(current_level, prev_level):
    """Re-implementation of formatLevelChange() from history.html"""
    if not current_level or not prev_level:
        return {"text": "-", "color": None}

    if current_level == prev_level:
        return {"text": "変化なし", "color": "--text-light"}

    try:
        cur_num = int(current_level.replace("Lv", ""))
        prev_num = int(prev_level.replace("Lv", ""))
    except (ValueError, AttributeError):
        return {"text": "-", "color": None}

    color = "--green" if cur_num > prev_num else "--error"
    return {"text": f"{prev_level}→{current_level}", "color": color}


def compute_comparisons(results):
    """Re-implementation of renderTable comparison logic from history.html.

    Returns a list of comparison dicts (one per result).
    Index 0 has no comparison (None). Index i>=1 has diff info.
    """
    comparisons = []
    for i, r in enumerate(results):
        if i == 0:
            comparisons.append(None)
        else:
            prev = results[i - 1]
            comparisons.append({
                "common_diff": format_diff(r["common_avg"], prev["common_avg"]),
                "track_diff": format_diff(r["track_avg"], prev["track_avg"]),
                "overall_diff": format_diff(r["overall_avg"], prev["overall_avg"]),
                "level_change": format_level_change(r["skill_level"], prev["skill_level"]),
            })
    return comparisons


# ---- Strategies ----

score_st = st.floats(min_value=0.0, max_value=4.0, allow_nan=False, allow_infinity=False)
score_str_st = score_st.map(lambda v: f"{v:.2f}")
level_st = st.sampled_from(["Lv1", "Lv2", "Lv3", "Lv4", "Lv5"])

result_st = st.fixed_dictionaries({
    "common_avg": score_str_st,
    "track_avg": score_str_st,
    "overall_avg": score_str_st,
    "skill_level": level_st,
})

# At least 2 results for comparison testing
results_list_st = st.lists(result_st, min_size=2, max_size=10)


# ---- Property 1: 前回比較の差分計算正当性 ----

@settings(max_examples=100)
@given(results=results_list_st)
def test_property1_diff_calculation_correctness(results):
    """
    Feature: aoki-feedback-improvements, Property 1: 前回比較の差分計算正当性

    任意の2件以上の履歴結果リストに対して、i番目（i≥1）の差分が
    results[i].score - results[i-1].score と一致し、
    初回（i=0）の差分は計算されないことを検証

    **Validates: Requirements 2.1**
    """
    comparisons = compute_comparisons(results)

    # i=0: no comparison
    assert comparisons[0] is None, "First result should have no comparison"

    # i>=1: diff matches results[i] - results[i-1]
    for i in range(1, len(results)):
        comp = comparisons[i]
        assert comp is not None, f"Result at index {i} should have comparison"

        for field in ["common_avg", "track_avg", "overall_avg"]:
            cur = float(results[i][field])
            prev = float(results[i - 1][field])
            expected_diff = cur - prev

            diff_key = field.replace("_avg", "_diff")
            if field == "overall_avg":
                diff_key = "overall_diff"
            elif field == "common_avg":
                diff_key = "common_diff"
            elif field == "track_avg":
                diff_key = "track_diff"

            result_text = comp[diff_key]["text"]

            if expected_diff > 0:
                parsed = float(result_text.replace("+", ""))
                assert abs(parsed - expected_diff) < 0.015, (
                    f"Field {field}: expected +{expected_diff:.2f}, got {result_text}"
                )
            elif expected_diff < 0:
                parsed = float(result_text)
                assert abs(parsed - expected_diff) < 0.015, (
                    f"Field {field}: expected {expected_diff:.2f}, got {result_text}"
                )
            else:
                assert result_text == "±0.00", (
                    f"Field {field}: expected ±0.00, got {result_text}"
                )


# ---- Property 2: 差分フォーマットの符号・値正当性 ----

@settings(max_examples=100)
@given(current=score_str_st, previous=score_str_st)
def test_property2_diff_format_sign_and_value(current, previous):
    """
    Feature: aoki-feedback-improvements, Property 2: 差分フォーマットの符号・値正当性

    任意の2つのスコア値（0.00〜4.00）に対して、
    差分>0→+X.XX/緑、差分<0→-X.XX/赤、差分=0→±0.00/グレーを検証

    **Validates: Requirements 2.3, 2.4, 2.5**
    """
    result = format_diff(current, previous)
    diff = float(current) - float(previous)

    if diff > 0:
        assert result["color"] == "--green", f"Positive diff should be green, got {result['color']}"
        assert result["text"].startswith("+"), f"Positive diff should start with +, got {result['text']}"
        parsed = float(result["text"].replace("+", ""))
        assert parsed > 0, f"Positive diff value should be > 0, got {parsed}"
    elif diff < 0:
        assert result["color"] == "--error", f"Negative diff should be error/red, got {result['color']}"
        assert result["text"].startswith("-"), f"Negative diff should start with -, got {result['text']}"
        parsed = float(result["text"])
        assert parsed < 0, f"Negative diff value should be < 0, got {parsed}"
    else:
        assert result["color"] == "--text-light", f"Zero diff should be text-light, got {result['color']}"
        assert result["text"] == "±0.00", f"Zero diff should be ±0.00, got {result['text']}"


# ---- Property 3: レベル変化フォーマットの正当性 ----

@settings(max_examples=100)
@given(current_level=level_st, prev_level=level_st)
def test_property3_level_change_format(current_level, prev_level):
    """
    Feature: aoki-feedback-improvements, Property 3: レベル変化フォーマットの正当性

    任意の2つのスキルレベル（Lv1〜Lv5）に対して、
    レベル変化時はLvX→LvY形式、上昇=緑、下降=赤を検証

    **Validates: Requirements 2.6**
    """
    result = format_level_change(current_level, prev_level)
    cur_num = int(current_level.replace("Lv", ""))
    prev_num = int(prev_level.replace("Lv", ""))

    if current_level == prev_level:
        assert result["text"] == "変化なし", f"Same level should show 変化なし, got {result['text']}"
        assert result["color"] == "--text-light", f"Same level color should be --text-light, got {result['color']}"
    else:
        expected_text = f"{prev_level}→{current_level}"
        assert result["text"] == expected_text, f"Expected {expected_text}, got {result['text']}"

        if cur_num > prev_num:
            assert result["color"] == "--green", f"Level up should be green, got {result['color']}"
        else:
            assert result["color"] == "--error", f"Level down should be error/red, got {result['color']}"
