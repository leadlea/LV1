"""POST /lv1/generate - テスト・ドリル生成ハンドラ"""

import json
import logging
import uuid

from backend.lib.bedrock_client import invoke_claude, strip_code_fence

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """AIカリキュラム「分業設計×依頼設計×品質担保×2ケース再現」の出題エージェント。
3問のテスト・ドリルをJSON形式で生成せよ。毎回異なるシナリオを使うこと。

出力JSON形式（これ以外のテキスト禁止）:
{"questions":[{"step":1,"type":"multiple_choice","prompt":"設問文","options":["A","B","C","D"],"context":null},{"step":2,"type":"free_text","prompt":"設問文","options":null,"context":null},{"step":3,"type":"scenario","prompt":"設問文","options":null,"context":"シナリオ説明"}]}

typeは "multiple_choice","free_text","scenario" のいずれか。stepは1から連番。"""


VALID_TYPES = {"multiple_choice", "free_text", "scenario"}


def _parse_questions(result: dict) -> list[dict]:
    """Bedrockレスポンスからquestionsを抽出しバリデーションする。"""
    # Claude応答のcontent[0].textからJSONを取得
    text = result.get("content", [{}])[0].get("text", "")
    text = strip_code_fence(text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse Bedrock response as JSON: %s", text[:200])
        raise ValueError("Bedrock response is not valid JSON")

    questions = data.get("questions")
    if not isinstance(questions, list) or len(questions) == 0:
        raise ValueError("Response missing 'questions' array or it is empty")

    validated = []
    for i, q in enumerate(questions):
        step = q.get("step")
        q_type = q.get("type")
        prompt = q.get("prompt")

        if not isinstance(step, int) or step < 1:
            raise ValueError(f"Question {i}: invalid step value")
        if q_type not in VALID_TYPES:
            raise ValueError(f"Question {i}: invalid type '{q_type}'")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError(f"Question {i}: prompt must be a non-empty string")

        validated.append({
            "step": step,
            "type": q_type,
            "prompt": prompt,
            "options": q.get("options") if q_type == "multiple_choice" else None,
            "context": q.get("context"),
        })

    return validated


def handler(event, context):
    """Lambda handler for POST /lv1/generate."""
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

    user_prompt = f"セッションID: {session_id}\n新しいテスト・ドリルを生成してください。"

    try:
        result = invoke_claude(SYSTEM_PROMPT, user_prompt)
        questions = _parse_questions(result)
    except (ValueError, Exception) as e:
        logger.error("Failed to generate questions: %s", str(e))
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
