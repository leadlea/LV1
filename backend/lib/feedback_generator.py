"""AIフィードバック生成モジュール（Bedrock Claude使用）"""

import json
import logging
import os
import re

from backend.lib.bedrock_client import invoke_claude, strip_code_fence

logger = logging.getLogger(__name__)

FEEDBACK_SYSTEM_PROMPT = """あなたはAIスキルアドバイザーです。
セルフチェック結果に基づき、以下の3セクションでフィードバックを日本語で生成してください。

1. strengths: 強み（現在のスキルで評価できる点を2〜3文で）
2. improvements: 改善ポイント（スコアが低い領域の具体的な改善提案を2〜3文で）
3. next_actions: 具体的な次のアクション（1〜3個の実行可能なステップを箇条書きで）

【重要】出力はJSON以外のテキストを一切含めず、以下の形式のみで返してください:
{"strengths": "...", "improvements": "...", "next_actions": "..."}
"""

_JSON_RE = re.compile(r'\{[^{}]*"strengths"[^{}]*"improvements"[^{}]*"next_actions"[^{}]*\}', re.DOTALL)


def _extract_json(text: str) -> dict | None:
    """テキストからフィードバックJSONを抽出する。複数の方法を試行。"""
    # 1. strip_code_fence → json.loads
    cleaned = strip_code_fence(text)
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. テキスト全体をそのままjson.loads
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, ValueError):
        pass

    # 3. 正規表現でJSON部分を抽出
    m = _JSON_RE.search(text)
    if m:
        try:
            return json.loads(m.group(0))
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def generate_feedback(track: str, answers: dict, scores: dict) -> dict | None:
    """
    Bedrock Claudeでフィードバックを生成する。
    bedrock_client.invoke_claude()を使用（リトライ付き）。
    失敗時はNoneを返す。
    """
    model_id = os.environ.get("BEDROCK_MODEL_ID")

    user_prompt = (
        f"トラック: {track}\n"
        f"回答: {json.dumps(answers, ensure_ascii=False)}\n"
        f"スコア: 共通平均={scores['common_avg']}, "
        f"トラック別平均={scores['track_avg']}, "
        f"総合平均={scores['overall_avg']}, "
        f"判定レベル={scores['skill_level']}\n\n"
        f"上記に基づいてJSON形式のみで回答してください。"
    )

    try:
        result = invoke_claude(
            system_prompt=FEEDBACK_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=1024,
            model_id=model_id,
            temperature=0.4,
        )
        raw_text = result["content"][0]["text"]
        logger.info("Bedrock raw response: %s", raw_text[:500])

        feedback = _extract_json(raw_text)
        if feedback is None:
            logger.warning("Could not parse feedback JSON from: %s", raw_text[:500])
            return None

        # 必須フィールドの存在チェック
        for key in ("strengths", "improvements", "next_actions"):
            if key not in feedback or not feedback[key]:
                logger.warning("Feedback missing or empty field: %s", key)
                return None

        return {
            "strengths": str(feedback["strengths"]),
            "improvements": str(feedback["improvements"]),
            "next_actions": str(feedback["next_actions"]),
        }
    except Exception:
        logger.exception("Failed to generate feedback")
        return None
