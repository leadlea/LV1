"""POST /lv2/generate - Lv2ケーススタディ生成ハンドラ"""

import json
import logging

from backend.lib.bedrock_client import invoke_claude, strip_code_fence

logger = logging.getLogger(__name__)

LV2_GENERATE_SYSTEM_PROMPT = """AIカリキュラム「業務プロセス設計×AI実行指示×成果物検証×改善サイクル」の出題エージェント。
コンサルティング業務で実際に発生しうる業務シナリオに基づく4ステップのケーススタディを生成せよ。
4問すべてが同一の業務シナリオに基づき、一貫性のあるケーススタディとすること。
毎回異なる業務シナリオを使うこと。

ステップ構成:
- ステップ1（業務プロセス設計）: scenario形式 — 業務シナリオを提示し、AI活用フローの設計を求める
- ステップ2（AI実行指示）: free_text形式 — ステップ1で設計したフローの一部について、AIへの具体的な指示文を作成させる
- ステップ3（成果物検証）: scenario形式 — AIが生成した成果物サンプルを提示し、品質評価と改善指示を求める
- ステップ4（改善サイクル）: free_text形式 — 一連のプロセスを振り返り、改善提案を求める

出力JSON形式（これ以外のテキスト禁止）:
{"questions":[{"step":1,"type":"scenario","prompt":"設問文","options":null,"context":"業務シナリオ説明"},{"step":2,"type":"free_text","prompt":"設問文","options":null,"context":"文脈説明"},{"step":3,"type":"scenario","prompt":"設問文","options":null,"context":"成果物サンプル"},{"step":4,"type":"free_text","prompt":"設問文","options":null,"context":"振り返り文脈"}]}

typeは "scenario" または "free_text" のみ。stepは1〜4の連番。contextは必ず含めること。"""

EXPECTED_NUM_QUESTIONS = 4
VALID_TYPES = {"scenario", "free_text"}
STEP_TYPE_MAP = {1: "scenario", 2: "free_text", 3: "scenario", 4: "free_text"}


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
        q_type = q.get("type", "").strip().lower()
        prompt = q.get("prompt")
        context = q.get("context") or ""

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

        validated.append({
            "step": step,
            "type": q_type,
            "prompt": prompt,
            "options": None,
            "context": context,
        })

    return validated


def handler(event, context):
    """Lambda handler for POST /lv2/generate."""
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

    user_prompt = f"セッションID: {session_id}\n新しいケーススタディを生成してください。"

    try:
        result = invoke_claude(LV2_GENERATE_SYSTEM_PROMPT, user_prompt, max_tokens=4096)
        questions = _parse_questions(result)
    except (ValueError, Exception) as e:
        logger.error("Failed to generate Lv2 questions: %s", str(e))
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
