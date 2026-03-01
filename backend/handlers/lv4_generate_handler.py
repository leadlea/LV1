"""POST /lv4/generate - Lv4組織横断ガバナンスシナリオ生成ハンドラ"""

import json
import logging

from backend.lib.bedrock_client import invoke_claude, strip_code_fence

logger = logging.getLogger(__name__)

LV4_GENERATE_SYSTEM_PROMPT = """AIカリキュラム「組織横断AI活用標準化×ガバナンス設計×持続的AI活用文化構築」の出題エージェント。
コンサルティング業務で実際に発生しうる大規模組織のAI活用標準化・ガバナンス課題に基づく6ステップの組織横断ガバナンスシナリオを生成せよ。
6問すべてが同一の組織シナリオに基づき、一貫性のある組織横断ガバナンスシナリオとすること。
毎回異なる組織シナリオを使うこと。

ステップ構成:
- ステップ1（AI活用標準化戦略）: scenario形式 — 組織全体のAI活用状況を提示し、標準化された活用方針・ガイドラインの策定を求める
- ステップ2（ガバナンスフレームワーク設計）: free_text形式 — ステップ1の組織状況に基づき、AI活用のポリシー・ルール・監査体制を含む包括的なガバナンスフレームワークの設計を求める
- ステップ3（組織横断AI推進体制構築）: scenario形式 — 複数部門のAI活用課題を提示し、横断的な推進体制・意思決定プロセス・コミュニケーション設計を求める
- ステップ4（AI活用文化醸成プログラム）: free_text形式 — 組織の現状文化を分析し、段階的な変革プログラム・成功指標・定着化施策の設計を求める
- ステップ5（リスク管理・コンプライアンス）: scenario形式 — AI活用に伴うリスクシナリオを提示し、法規制・倫理基準への準拠を含む包括的なリスク管理体制の設計を求める
- ステップ6（中長期AI活用ロードマップ）: free_text形式 — 組織全体のAI活用実績データを提示し、中長期AI活用計画と定量的な成果指標（KPI）の策定を求める

出力JSON形式（これ以外のテキスト禁止）:
{"questions":[{"step":1,"type":"scenario","prompt":"設問文","options":null,"context":"組織シナリオ説明"},{"step":2,"type":"free_text","prompt":"設問文","options":null,"context":"文脈説明"},{"step":3,"type":"scenario","prompt":"設問文","options":null,"context":"複数部門課題シナリオ"},{"step":4,"type":"free_text","prompt":"設問文","options":null,"context":"組織文化の現状"},{"step":5,"type":"scenario","prompt":"設問文","options":null,"context":"リスクシナリオ"},{"step":6,"type":"free_text","prompt":"設問文","options":null,"context":"AI活用実績データ"}]}

typeは "scenario" または "free_text" のみ。stepは1〜6の連番。contextは必ず含めること。"""

EXPECTED_NUM_QUESTIONS = 6
STEP_TYPE_MAP = {1: "scenario", 2: "free_text", 3: "scenario", 4: "free_text", 5: "scenario", 6: "free_text"}


def _parse_questions(result: dict) -> list[dict]:
    """Bedrockレスポンスからquestionsを抽出しバリデーションする。"""
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
        result = invoke_claude(LV4_GENERATE_SYSTEM_PROMPT, user_prompt)
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
