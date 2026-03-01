"""POST /lv2/grade - Lv2回答採点+レビューハンドラ"""

import json
import logging

from backend.lib.bedrock_client import invoke_claude, strip_code_fence
from backend.lib.lv2_reviewer import generate_lv2_feedback
from backend.lib.threshold_resolver import resolve_passed

logger = logging.getLogger(__name__)

LV2_GRADE_SYSTEM_PROMPT = """あなたはAIカリキュラム「業務プロセス設計×AI実行指示×成果物検証×改善サイクル」の採点エージェントです。

ステップごとの採点基準:
- ステップ1（業務プロセス設計）: AIと人間の役割分担が明確か、フローが具体的で実行可能か、業務シナリオの制約を考慮しているか
- ステップ2（AI実行指示）: 目的・制約・出力形式が構造化されているか、業務文脈に適した指示か、AIの特性を活かした指示か
- ステップ3（成果物検証）: 業務要件との適合性を評価できているか、正確性の問題を指摘できているか、改善指示が具体的か
- ステップ4（改善サイクル）: 改善点の根拠が明確か、次回に活かせる具体的な提案か、プロセス全体を俯瞰できているか

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
        logger.error("Failed to parse Lv2 Grader response as JSON: %s", text[:200])
        raise ValueError("Lv2 Grader response is not valid JSON")

    passed = data.get("passed")
    score = data.get("score")

    if not isinstance(passed, bool):
        raise ValueError("passed must be a boolean")
    if not isinstance(score, int) or score < 0 or score > 100:
        raise ValueError("score must be an integer between 0 and 100")

    return {"passed": passed, "score": score}


def handler(event, context):
    """Lambda handler for POST /lv2/grade."""
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
    if not isinstance(step, int) or step < 1 or step > 4:
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "step must be an integer between 1 and 4"}),
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
        grade_raw = invoke_claude(LV2_GRADE_SYSTEM_PROMPT, user_prompt)
        grade_result = _parse_grade_result(grade_raw)
        grade_result["passed"] = resolve_passed(level=2, score=grade_result["score"])

        # 2. レビュー（フィードバック・解説）生成
        review = generate_lv2_feedback(question, answer, grade_result)
    except (ValueError, Exception) as e:
        logger.error("Failed to grade/review Lv2: %s", str(e))
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
