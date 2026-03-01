"""POST /lv3/generate - Lv3プロジェクトリーダーシップシナリオ生成ハンドラ"""

import json
import logging

from backend.lib.bedrock_client import invoke_claude, strip_code_fence

logger = logging.getLogger(__name__)

FAST_MODEL_ID = "jp.anthropic.claude-sonnet-4-5-20250929-v1:0"

LV3_GENERATE_SYSTEM_PROMPT = """AI導入プロジェクトリーダーシップの出題。同一組織シナリオで5問生成。毎回異なるシナリオ。
step1:scenario(プロジェクト計画策定) step2:free_text(AI活用ロードマップ) step3:scenario(AI導入計画立案) step4:scenario(スキル育成計画) step5:free_text(ROI評価改善)
JSON出力のみ:{"questions":[{"step":1,"type":"scenario","prompt":"設問","options":null,"context":"説明"},{"step":2,"type":"free_text","prompt":"設問","options":null,"context":"説明"},{"step":3,"type":"scenario","prompt":"設問","options":null,"context":"説明"},{"step":4,"type":"scenario","prompt":"設問","options":null,"context":"説明"},{"step":5,"type":"free_text","prompt":"設問","options":null,"context":"説明"}]}"""

EXPECTED_NUM_QUESTIONS = 5
VALID_TYPES = {"scenario", "free_text"}
STEP_TYPE_MAP = {1: "scenario", 2: "free_text", 3: "scenario", 4: "scenario", 5: "free_text"}


def _parse_questions(result: dict) -> list[dict]:
    """Bedrockレスポンスからquestionsを抽出しバリデーションする。"""
    stop_reason = result.get("stop_reason")
    if stop_reason == "max_tokens":
        logger.warning("Bedrock response was truncated due to max_tokens limit")

    text = result.get("content", [{}])[0].get("text", "")
    text = strip_code_fence(text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse Bedrock response as JSON: %s", text[:200])
        raise ValueError("Bedrock response is not valid JSON")

    questions = data.get("questions")
    if not isinstance(questions, list) or len(questions) != EXPECTED_NUM_QUESTIONS:
        raise ValueError(
            f"Response must contain exactly {EXPECTED_NUM_QUESTIONS} questions, "
            f"got {len(questions) if isinstance(questions, list) else 'none'}"
        )

    validated = []
    for i, q in enumerate(questions):
        step = q.get("step")
        q_type = q.get("type")
        prompt = q.get("prompt")
        context = q.get("context")

        expected_step = i + 1
        if not isinstance(step, int) or step != expected_step:
            raise ValueError(f"Question {i}: step must be {expected_step}, got {step}")

        expected_type = STEP_TYPE_MAP[expected_step]
        if q_type != expected_type:
            raise ValueError(
                f"Question {i}: step {expected_step} must be type '{expected_type}', got '{q_type}'"
            )

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"Question {i}: prompt must be a non-empty string")

        if not isinstance(context, str) or not context.strip():
            raise ValueError(f"Question {i}: context must be a non-empty string")

        validated.append({
            "step": step,
            "type": q_type,
            "prompt": prompt,
            "options": None,
            "context": context,
        })

    return validated


def handler(event, context):
    """Lambda handler for POST /lv3/generate."""
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Invalid JSON in request body"}),
        }

    session_id = body.get("session_id")
    if not session_id or not isinstance(session_id, str):
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "session_id is required"}),
        }

    user_prompt = f"セッションID: {session_id}\n新しいプロジェクトリーダーシップシナリオを生成してください。"

    try:
        result = invoke_claude(LV3_GENERATE_SYSTEM_PROMPT, user_prompt, max_tokens=4096, model_id=FAST_MODEL_ID)
        questions = _parse_questions(result)
    except (ValueError, Exception) as e:
        logger.error("Failed to generate Lv3 questions: %s", str(e))
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "テスト生成に失敗しました。リトライしてください。"}),
        }

    return {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": json.dumps({
            "session_id": session_id,
            "questions": questions,
        }, ensure_ascii=False),
    }
