"""Lv4レビューエージェント（Reviewer） - Lv4採点結果をもとにフィードバック・解説を生成する。"""

import json
import logging

from backend.lib.bedrock_client import invoke_claude, strip_code_fence

logger = logging.getLogger(__name__)

LV4_REVIEW_SYSTEM_PROMPT = """あなたはAIカリキュラム「組織横断AI活用標準化×ガバナンス設計×持続的AI活用文化構築」のレビューエージェントです。

採点結果をもとに、学習者に対するフィードバックと解説を生成してください。

フィードバックでは:
- 回答の良かった点と改善点を具体的に指摘する
- 組織横断AI推進者としての具体的な改善アクションを含める
- Lv4の学習目標（組織横断AI活用標準化・ガバナンス設計・持続的AI活用文化構築）に沿った助言を行う
- ベストプラクティスや実務での応用ポイントを含める

解説では:
- 正解の考え方や背景知識を説明する
- コンサルティング実務での組織横断ガバナンス応用例を含める

出力は必ず以下のJSON形式で返してください。それ以外のテキストは含めないでください:
{
  "feedback": "フィードバック文",
  "explanation": "解説文"
}"""


def generate_lv4_feedback(question: dict, answer: str, grade_result: dict) -> dict:
    """
    Lv4採点結果をもとにフィードバック・解説を生成する。

    Args:
        question: 設問データ
        answer: ユーザーの回答
        grade_result: 採点結果 {"passed": bool, "score": int}

    Returns:
        {"feedback": str, "explanation": str}

    Raises:
        ValueError: Bedrockレスポンスのパースに失敗した場合
    """
    user_prompt = (
        f"設問: {json.dumps(question, ensure_ascii=False)}\n"
        f"回答: {answer}\n"
        f"採点結果: {json.dumps(grade_result, ensure_ascii=False)}\n\n"
        "この回答に対するフィードバックと解説を生成してください。"
    )

    result = invoke_claude(LV4_REVIEW_SYSTEM_PROMPT, user_prompt)

    text = result.get("content", [{}])[0].get("text", "")
    text = strip_code_fence(text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse Lv4 Reviewer response as JSON: %s", text[:200])
        raise ValueError("Lv4 Reviewer response is not valid JSON")

    feedback = data.get("feedback")
    explanation = data.get("explanation")

    if not isinstance(feedback, str) or not feedback.strip():
        raise ValueError("feedback must be a non-empty string")
    if not isinstance(explanation, str) or not explanation.strip():
        raise ValueError("explanation must be a non-empty string")

    return {"feedback": feedback, "explanation": explanation}
