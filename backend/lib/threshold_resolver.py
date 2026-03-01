import os
import logging

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 30


def get_threshold(level: int) -> int:
    """指定レベルの合格閾値を環境変数から取得する。

    Args:
        level: レベル番号 (1-4)

    Returns:
        合格閾値 (0-100の整数)

    バリデーション:
        - 環境変数が未設定 → デフォルト値30
        - 整数変換不可 → デフォルト値30 + 警告ログ
        - 0未満 → 0に補正 + 警告ログ
        - 100超 → 100に補正 + 警告ログ
    """
    env_key = f"PASS_THRESHOLD_LV{level}"
    raw = os.environ.get(env_key)

    if raw is None:
        return DEFAULT_THRESHOLD

    try:
        value = int(raw)
    except (ValueError, TypeError):
        logger.warning(
            "Invalid threshold value for %s: %r, using default %d",
            env_key, raw, DEFAULT_THRESHOLD,
        )
        return DEFAULT_THRESHOLD

    if value < 0:
        logger.warning(
            "Threshold for %s is below 0 (%d), clamping to 0",
            env_key, value,
        )
        return 0

    if value > 100:
        logger.warning(
            "Threshold for %s exceeds 100 (%d), clamping to 100",
            env_key, value,
        )
        return 100

    return value


def resolve_passed(level: int, score: int) -> bool:
    """スコアが閾値以上かどうかを判定する。

    Args:
        level: レベル番号 (1-4)
        score: AIが返したスコア (0-100)

    Returns:
        True if score >= threshold, False otherwise
    """
    threshold = get_threshold(level)
    return score >= threshold
