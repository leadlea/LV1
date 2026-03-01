"""POST /lv4/grade - Lv4回答採点+レビューハンドラ"""

import json
import logging

from backend.lib.bedrock_client import invoke_claude, strip_code_fence
from backend.lib.lv4_reviewer import generate_lv4_feedback

logger = logging.getLogger(__name__)

LV4_GRADE_SYSTEM_PROMPT = """あなたはAIカリキュラム「組織横断AI活用標準化×ガバナンス設計×持続的AI活用文化構築」の採点エージェントです。

ステップごとの採点基準:
- ステップ1（AI活用標準化戦略）: 組織全体のAI活用状況分析が的確か、標準化方針が部門横断で適用可能か、ガイドラインが具体的か
- ステップ2（ガバナンスフレームワーク設計）: ポリシー・ルールが包括的か、監査体制が実効的か、責任分担が明確か
- ステップ3（組織横断AI推進体制構築）: 複数部門の課題把握が的確か、推進体制が実効的か、意思決定プロセスが明確か、コミュニケーション設計が具体的か
- ステップ4（AI活用文化醸成プログラム）: 現状文化の分析が的確か、変革プログラムが段階的か、成功指標が測定可能か、定着化施策が具体的か
- ステップ5（リスク管理・コンプライアンス）: リスクシナリオの特定が網羅的か、法規制・倫理基準への準拠が考慮されているか、リスク管理体制が包括的か
- ステップ6（中長期AI活用ロードマップ）: 中長期計画が実現可能か、KPIが定量的か、評価サイクルが設計されているか、組織全体の視点があるか

出力は必ず以下のJSON形式で返してください。それ以外のテキストは含めないでください:
{
  "passed": true または false,
  "score": 0〜100の整数
}

60点以上を合格とする。"""


def _parse_grade_result(result: dict) -> dict:
    """Bedrockレスポンスから採点結果を抽出しバリデーションする。"""
    text = result.get("content", [{}])[0].get("text", "")
    text = strip_code_fence(text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse Lv4 Grader response as JSON: %s", text[:200])
        raise ValueError("Lv4 Grader response is not valid JSON")

    passed = data.get("passed")
    score = data.get("score")

    if not isinstance(passed, bool):
        raise ValueError("passed must be a boolean")
    if not isinstance(score, int) or score < 0 or score > 100:
        raise ValueError("score must be an integer between 0 and 100")

    return {"passed": passed, "score": score}


def handler(event, context):
    """Lambda handler for POST /lv4/grade."""
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Invalid JSON in request body"}),
        }

    session_id = body.get("session_id")
    step = body.get("step")
    question = body.get("question")
    answer = body.get("answer")

    if not session_id or not isinstance(session_id, str):
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "session_id is required"}),
        }
    if not isinstance(step, int) or step < 1 or step > 6:
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "step must be an integer between 1 and 6"}),
        }
    if not isinstance(question, dict):
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "question is required"}),
        }
    if not isinstance(answer, str) or not answer.strip():
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "answer is required"}),
        }

    user_prompt = (
        f"設問: {json.dumps(question, ensure_ascii=False)}\n"
        f"回答: {answer}\n\n"
        "この回答を採点してください。"
    )

    try:
        # 1. 採点実行
        grade_raw = invoke_claude(LV4_GRADE_SYSTEM_PROMPT, user_prompt)
        grade_result = _parse_grade_result(grade_raw)

        # 2. レビュー（フィードバック・解説）生成
        review = generate_lv4_feedback(question, answer, grade_result)
    except (ValueError, Exception) as e:
        logger.error("Failed to grade/review Lv4: %s", str(e))
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "採点に失敗しました。リトライしてください。"}),
        }

    return {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": json.dumps({
            "session_id": session_id,
            "step": step,
            "passed": grade_result["passed"],
            "score": grade_result["score"],
            "feedback": review["feedback"],
            "explanation": review["explanation"],
        }, ensure_ascii=False),
    }
