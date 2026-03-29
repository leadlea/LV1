"""AIフィードバック生成モジュール（Bedrock Claude使用）"""

import json
import logging

from backend.lib.bedrock_client import invoke_claude, strip_code_fence

logger = logging.getLogger(__name__)

FEEDBACK_SYSTEM_PROMPT = """あなたはAIスキルアドバイザーです。
セルフチェック結果に基づき、以下の3セクションでフィードバックを生成してください。

1. strengths: 強み（現在のスキルで評価できる点）
2. improvements: 改善ポイント（スコアが低い領域の具体的な改善提案）
3. next_actions: 具体的な次のアクション（1〜3個の実行可能なステップ）

出力は必ず以下のJSON形式で返してください:
{"strengths": "...", "improvements": "...", "next_actions": "..."}
"""


def generate_feedback(track: str, answers: dict, scores: dict) -> dict | None:
    """
    Bedrock Claudeでフィードバックを生成する。
    bedrock_client.invoke_claude()を使用（リトライ付き）。
    失敗時はNoneを返す。
    """
    user_prompt = (
        f"トラック: {track}\n"
        f"回答: {json.dumps(answers, ensure_ascii=False)}\n"
        f"スコア: 共通平均={scores['common_avg']}, "
        f"トラック別平均={scores['track_avg']}, "
        f"総合平均={scores['overall_avg']}, "
        f"判定レベル={scores['skill_level']}"
    )

    try:
        result = invoke_claude(
            system_prompt=FEEDBACK_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=1024,
            temperature=0.4,
        )
        raw_text = result["content"][0]["text"]
        cleaned = strip_code_fence(raw_text)
        feedback = json.loads(cleaned)

        # 必須フィールドの存在チェック
        for key in ("strengths", "improvements", "next_actions"):
            if key not in feedback or not feedback[key]:
                logger.warning("Feedback missing or empty field: %s", key)
                return None

        return {
            "strengths": feedback["strengths"],
            "improvements": feedback["improvements"],
            "next_actions": feedback["next_actions"],
        }
    except Exception:
        logger.exception("Failed to generate feedback")
        return None
