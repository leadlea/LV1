"""POST /lv1/grade - 回答採点+レビューハンドラ"""

import json
import logging

from backend.lib.bedrock_client import invoke_claude, strip_code_fence
from backend.lib.reviewer import generate_feedback
from backend.lib.threshold_resolver import resolve_passed

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """あなたはAIカリキュラム「分業設計×依頼設計×品質担保×2ケース再現」の採点エージェントです。

ユーザーの回答を設問に照らして採点してください。

採点基準:
- 設問の意図を正しく理解しているか
- 具体的かつ実践的な回答になっているか
- カリキュラムの学習目標に沿った内容か

出力は必ず以下のJSON形式で返してください。それ以外のテキストは含めないでください:
{
  "passed": true または false,
  "score": 0〜100の整数
}"""


def _parse_grade_result(result: dict) -> dict:
    """Bedrockレスポンスから採点結果を抽出しバリデーションする。"""
    text = result.get("content", [{}])[0].get("text", "")
    text = strip_code_fence(text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse Grader response as JSON: %s", text[:200])
        raise ValueError("Grader response is not valid JSON")

    passed = data.get("passed")
    score = data.get("score")

    if not isinstance(passed, bool):
        raise ValueError("passed must be a boolean")
    if not isinstance(score, int) or score < 0 or score > 100:
        raise ValueError("score must be an integer between 0 and 100")

    return {"passed": passed, "score": score}


def handler(event, context):
    """Lambda handler for POST /lv1/grade."""
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
    if not isinstance(step, int) or step < 1:
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "step must be a positive integer"}),
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
        grade_raw = invoke_claude(SYSTEM_PROMPT, user_prompt)
        grade_result = _parse_grade_result(grade_raw)
        grade_result["passed"] = resolve_passed(level=1, score=grade_result["score"])

        # 2. レビュー（フィードバック・解説）生成
        review = generate_feedback(question, answer, grade_result)
    except (ValueError, Exception) as e:
        logger.error("Failed to grade/review: %s", str(e))
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
