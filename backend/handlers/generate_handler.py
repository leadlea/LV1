"""POST /lv1/generate - テスト・ドリル生成ハンドラ"""

import json
import logging
import uuid

from backend.lib.bedrock_client import invoke_claude

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """あなたはAIカリキュラム「分業設計×依頼設計×品質担保×2ケース再現」の出題エージェントです。

以下の4つのテーマに基づいて、ステップバイステップで進行するテスト・ドリルを生成してください:
1. 分業設計: チーム内での役割分担と責任範囲の設計
2. 依頼設計: 他チーム・他者への依頼の構造化と明確化
3. 品質担保: 成果物の品質を保証するためのレビュー・テスト設計
4. 2ケース再現: 異なるシナリオでの適用力を確認する2つのケーススタディ

毎回異なる具体的なシナリオ・状況設定を用いて、新鮮な問題を生成してください。
同じ問題を繰り返さず、多様な業界・プロジェクト規模・チーム構成を題材にしてください。

出力は必ず以下のJSON形式で返してください。それ以外のテキストは含めないでください:
{
  "questions": [
    {
      "step": 1,
      "type": "multiple_choice" または "free_text" または "scenario",
      "prompt": "設問文",
      "options": ["選択肢1", "選択肢2", ...] (multiple_choiceの場合のみ、それ以外はnull),
      "context": "補足情報やシナリオ説明" (必要な場合のみ、不要ならnull)
    }
  ]
}

questionsは4〜6問で構成し、stepは1から連番にしてください。
type は "multiple_choice", "free_text", "scenario" のいずれかを使い分けてください。"""


VALID_TYPES = {"multiple_choice", "free_text", "scenario"}


def _parse_questions(result: dict) -> list[dict]:
    """Bedrockレスポンスからquestionsを抽出しバリデーションする。"""
    # Claude応答のcontent[0].textからJSONを取得
    text = result.get("content", [{}])[0].get("text", "")

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
