"""POST /lv4/generate - Lv4組織横断ガバナンスシナリオ生成ハンドラ"""

import json
import logging

from backend.lib.bedrock_client import invoke_claude, strip_code_fence

logger = logging.getLogger(__name__)

FAST_MODEL_ID = "jp.anthropic.claude-sonnet-4-5-20250929-v1:0"

LV4_GENERATE_SYSTEM_PROMPT = """組織横断AI活用ガバナンスの出題。同一組織シナリオで6問生成。毎回異なるシナリオ。各設問のpromptは1〜2文、contextは2〜3文で簡潔に。
step1:scenario(AI活用標準化戦略) step2:free_text(ガバナンス設計) step3:scenario(組織横断推進体制) step4:free_text(文化醸成プログラム) step5:scenario(リスク管理) step6:free_text(中長期ロードマップ)
JSON出力のみ:{"questions":[{"step":1,"type":"scenario","prompt":"設問","options":null,"context":"説明"},{"step":2,"type":"free_text","prompt":"設問","options":null,"context":"説明"},{"step":3,"type":"scenario","prompt":"設問","options":null,"context":"説明"},{"step":4,"type":"free_text","prompt":"設問","options":null,"context":"説明"},{"step":5,"type":"scenario","prompt":"設問","options":null,"context":"説明"},{"step":6,"type":"free_text","prompt":"設問","options":null,"context":"説明"}]}"""

EXPECTED_NUM_QUESTIONS = 6
STEP_TYPE_MAP = {1: "scenario", 2: "free_text", 3: "scenario", 4: "free_text", 5: "scenario", 6: "free_text"}


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
    """Lambda handler for POST /lv4/generate."""
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

    user_prompt = f"セッションID: {session_id}\n新しい組織横断ガバナンスシナリオを生成してください。"

    try:
        result = invoke_claude(LV4_GENERATE_SYSTEM_PROMPT, user_prompt, max_tokens=4096, model_id=FAST_MODEL_ID, temperature=0.2)
        questions = _parse_questions(result)
    except (ValueError, Exception) as e:
        logger.error("Failed to generate Lv4 questions: %s", str(e))
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
