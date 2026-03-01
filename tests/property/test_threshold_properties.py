"""Property-based tests for threshold_resolver.

Feature: configurable-pass-threshold

Property 1: 閾値判定の正当性
Property 2: スコア保持
Property 3: 閾値バリデーション結果の範囲保証
Property 4: 不正値検出時の警告ログ
Property 5: レベル別環境変数の正しい参照

Validates: Requirements 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4
"""

import json
import logging
import os
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.lib.threshold_resolver import get_threshold, resolve_passed
from backend.handlers.grade_handler import handler


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_LEVELS = st.integers(min_value=1, max_value=4)
_SCORES = st.integers(min_value=0, max_value=100)
_THRESHOLDS = st.integers(min_value=0, max_value=100)

# Strategy for arbitrary env-var values: valid ints, out-of-range ints,
# non-integer strings, and empty strings.
# Exclude null bytes since os.environ rejects them.
_SAFE_TEXT = st.text(
    alphabet=st.characters(blacklist_characters="\x00"),
    min_size=0,
    max_size=20,
)
_ENV_VALUES = st.one_of(
    st.integers().map(str),                          # any integer as string
    _SAFE_TEXT,                                       # arbitrary text (incl. empty)
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bedrock_grade_response(passed: bool, score: int) -> dict:
    """Build a mock Bedrock response for the grade handler."""
    return {"content": [{"text": json.dumps({"passed": passed, "score": score})}]}


def _api_event(session_id: str, step: int, answer: str) -> dict:
    """Build a minimal valid API Gateway event for the grade handler."""
    return {
        "body": json.dumps({
            "session_id": session_id,
            "step": step,
            "question": {"step": step, "type": "free_text", "prompt": "Q?"},
            "answer": answer,
        })
    }


# ---------------------------------------------------------------------------
# Property 1: 閾値判定の正当性
# ---------------------------------------------------------------------------

@given(level=_LEVELS, score=_SCORES, threshold=_THRESHOLDS)
@settings(max_examples=100)
def test_threshold_judgment_correctness(level, score, threshold):
    """Property 1: 閾値判定の正当性

    任意のスコア(0-100)と閾値(0-100)に対して、resolve_passed(level, score)の
    結果は score >= threshold と等しくなること。

    **Validates: Requirements 2.1, 2.2, 2.3**
    """
    env_key = f"PASS_THRESHOLD_LV{level}"
    with patch.dict(os.environ, {env_key: str(threshold)}):
        result = resolve_passed(level, score)

    assert result == (score >= threshold)


# ---------------------------------------------------------------------------
# Property 2: スコア保持
# ---------------------------------------------------------------------------

@given(
    score=_SCORES,
    threshold=_THRESHOLDS,
)
@settings(max_examples=100)
def test_score_preserved(score, threshold):
    """Property 2: スコア保持

    任意のAIスコア(0-100)と閾値設定に対して、Grade Handlerのレスポンスに
    含まれるscore値はAIが返した値と一致すること。

    **Validates: Requirements 2.4**
    """
    event = _api_event("test-session", 1, "my answer")

    with (
        patch.dict(os.environ, {"PASS_THRESHOLD_LV1": str(threshold)}),
        patch("backend.handlers.grade_handler.invoke_claude") as mock_invoke,
        patch("backend.handlers.grade_handler.generate_feedback") as mock_review,
    ):
        mock_invoke.return_value = _bedrock_grade_response(True, score)
        mock_review.return_value = {"feedback": "Good", "explanation": "OK"}
        resp = handler(event, None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["score"] == score


# ---------------------------------------------------------------------------
# Property 3: 閾値バリデーション結果の範囲保証
# ---------------------------------------------------------------------------

@given(level=_LEVELS, env_value=_ENV_VALUES)
@settings(max_examples=100)
def test_threshold_validation_range(level, env_value):
    """Property 3: 閾値バリデーション結果の範囲保証

    任意の環境変数値（整数、非整数文字列、負数、100超の値、空文字列）に対して、
    get_threshold(level)の返却値は常に0以上100以下の整数であること。

    **Validates: Requirements 3.1, 3.2, 3.3**
    """
    env_key = f"PASS_THRESHOLD_LV{level}"
    with patch.dict(os.environ, {env_key: env_value}):
        result = get_threshold(level)

    assert isinstance(result, int)
    assert 0 <= result <= 100


# ---------------------------------------------------------------------------
# Property 4: 不正値検出時の警告ログ
# ---------------------------------------------------------------------------

# Invalid values: non-integer strings, below 0, above 100
_INVALID_NON_INT = st.text(
    alphabet=st.characters(blacklist_characters="\x00"),
    min_size=1,
    max_size=20,
).filter(lambda s: not _is_int(s))
_INVALID_BELOW_ZERO = st.integers(max_value=-1).map(str)
_INVALID_ABOVE_100 = st.integers(min_value=101).map(str)
_INVALID_ENV_VALUES = st.one_of(
    _INVALID_NON_INT,
    _INVALID_BELOW_ZERO,
    _INVALID_ABOVE_100,
    st.just(""),  # empty string is also invalid
)

# Valid values: integers 0-100
_VALID_ENV_VALUES = st.integers(min_value=0, max_value=100).map(str)


def _is_int(s: str) -> bool:
    """Check if a string can be parsed as an integer."""
    try:
        int(s)
        return True
    except (ValueError, TypeError):
        return False


@given(level=_LEVELS, env_value=_INVALID_ENV_VALUES)
@settings(max_examples=100)
def test_invalid_value_warning_log(level, env_value):
    """Property 4: 不正値検出時の警告ログ (invalid values)

    任意の不正な環境変数値（非整数文字列、0未満、100超）に対して、
    get_threshold(level)は警告ログを出力すること。

    **Validates: Requirements 3.4**
    """
    env_key = f"PASS_THRESHOLD_LV{level}"
    logger = logging.getLogger("backend.lib.threshold_resolver")

    with (
        patch.dict(os.environ, {env_key: env_value}),
        patch.object(logger, "warning") as mock_warning,
    ):
        get_threshold(level)

    assert mock_warning.call_count >= 1, (
        f"Expected warning log for invalid value {env_value!r}, got none"
    )


@given(level=_LEVELS, env_value=_VALID_ENV_VALUES)
@settings(max_examples=100)
def test_valid_value_no_warning_log(level, env_value):
    """Property 4 (complement): 有効な値では警告ログを出力しないこと。

    有効な値(0-100の整数)に対しては警告ログを出力しないこと。

    **Validates: Requirements 3.4**
    """
    env_key = f"PASS_THRESHOLD_LV{level}"
    logger = logging.getLogger("backend.lib.threshold_resolver")

    with (
        patch.dict(os.environ, {env_key: env_value}),
        patch.object(logger, "warning") as mock_warning,
    ):
        get_threshold(level)

    assert mock_warning.call_count == 0, (
        f"Unexpected warning log for valid value {env_value!r}"
    )


# ---------------------------------------------------------------------------
# Property 5: レベル別環境変数の正しい参照
# ---------------------------------------------------------------------------

@given(
    level=_LEVELS,
    target_value=_THRESHOLDS,
    other_value=_THRESHOLDS,
)
@settings(max_examples=100)
def test_level_env_var_mapping(level, target_value, other_value):
    """Property 5: レベル別環境変数の正しい参照

    各レベル(1-4)に対して、get_threshold(level)はPASS_THRESHOLD_LV{level}
    環境変数の値を参照すること。異なるレベルの環境変数を参照しないこと。

    **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
    """
    all_levels = [1, 2, 3, 4]

    # Set the target level's env var to target_value,
    # and all other levels to other_value.
    env_patch = {}
    for lv in all_levels:
        if lv == level:
            env_patch[f"PASS_THRESHOLD_LV{lv}"] = str(target_value)
        else:
            env_patch[f"PASS_THRESHOLD_LV{lv}"] = str(other_value)

    with patch.dict(os.environ, env_patch):
        result = get_threshold(level)

    assert result == target_value
