"""POST /lv3/grade - Lv3回答採点+レビューハンドラ"""

import json
import logging

from backend.lib.bedrock_client import invoke_claude, strip_code_fence
from backend.lib.lv3_reviewer import generate_lv3_feedback
from backend.lib.threshold_resolver import resolve_passed

logger = logging.getLogger(__name__)

LV3_GRADE_SYSTEM_PROMPT = """あなたはAIカリキュラム「AI活用プロジェクトリーダーシップ×チームAI戦略策定×AI導入計画立案×スキル育成計画×ROI評価改善」の採点エージェントです。

ステップごとの採点基準:
- ステップ1（AI活用プロジェクトリーダーシップ）: プロジェクト計画の実現可能性、目的・スコープの明確さ、体制・スケジュールの具体性
- ステップ2（チームAI戦略策定）: AI活用ロードマップの論理的整合性、短期・中期・長期の段階性、組織状況との適合性
- ステップ3（AI導入計画立案）: 導入計画の具体性、リソース配分の妥当性、リスク対策の網羅性
- ステップ4（スキル育成計画）: 育成プランの段階性、評価指標の定量性、チームメンバーのスキル状況への適合性
- ステップ5（ROI評価改善）: ROI評価の定量性、改善施策の実現可能性、データに基づく分析の深さ

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
        logger.error("Failed to parse Lv3 Grader response as JSON: %s", text[:200])
        raise ValueError("Lv3 Grader response is not valid JSON")

    passed = data.get("passed")
    score = data.get("score")

    if not isinstance(passed, bool):
        raise ValueError("passed must be a boolean")
    if not isinstance(score, int) or score < 0 or score > 100:
        raise ValueError("score must be an integer between 0 and 100")

    return {"passed": passed, "score": score}


def handler(event, context):
    """Lambda handler for POST /lv3/grade."""
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
    if not isinstance(step, int) or step < 1 or step > 5:
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "step must be an integer between 1 and 5"}),
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
        grade_raw = invoke_claude(LV3_GRADE_SYSTEM_PROMPT, user_prompt)
        grade_result = _parse_grade_result(grade_raw)
        grade_result["passed"] = resolve_passed(level=3, score=grade_result["score"])

        # 2. レビュー（フィードバック・解説）生成
        review = generate_lv3_feedback(question, answer, grade_result)
    except (ValueError, Exception) as e:
        logger.error("Failed to grade/review Lv3: %s", str(e))
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
