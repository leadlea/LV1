"""POST /lv3/generate - Lv3プロジェクトリーダーシップシナリオ生成ハンドラ"""

import json
import logging

from backend.lib.bedrock_client import invoke_claude, strip_code_fence

logger = logging.getLogger(__name__)

LV3_GENERATE_SYSTEM_PROMPT = """AIカリキュラム「AI活用プロジェクトリーダーシップ×チームAI戦略策定×AI導入計画立案×スキル育成計画×ROI評価改善」の出題エージェント。
コンサルティング業務で実際に発生しうるAI導入プロジェクトの組織シナリオに基づく5ステップのプロジェクトリーダーシップシナリオを生成せよ。
5問すべてが同一の組織シナリオに基づき、一貫性のあるプロジェクトリーダーシップシナリオとすること。
毎回異なる組織シナリオを使うこと。

ステップ構成:
- ステップ1（AI活用プロジェクトリーダーシップ）: scenario形式 — 組織のAI活用課題を提示し、プロジェクト計画（目的・スコープ・体制・スケジュール）の策定を求める
- ステップ2（チームAI戦略策定）: free_text形式 — ステップ1の組織状況に基づき、チーム全体のAI活用ロードマップ（短期・中期・長期）の策定を求める
- ステップ3（AI導入計画立案）: scenario形式 — 具体的なAI導入対象業務を提示し、実行計画・リソース配分・リスク対策を含む導入計画の立案を求める
- ステップ4（スキル育成計画）: scenario形式 — チームメンバーのスキル状況データを提示し、段階的な育成プランと評価指標の設計を求める
- ステップ5（ROI評価改善）: free_text形式 — AI活用の実績データを提示し、定量的なROI評価と改善施策の立案を求める

出力JSON形式（これ以外のテキスト禁止）:
{"questions":[{"step":1,"type":"scenario","prompt":"設問文","options":null,"context":"組織シナリオ説明"},{"step":2,"type":"free_text","prompt":"設問文","options":null,"context":"文脈説明"},{"step":3,"type":"scenario","prompt":"設問文","options":null,"context":"AI導入対象業務シナリオ"},{"step":4,"type":"scenario","prompt":"設問文","options":null,"context":"スキル状況データ"},{"step":5,"type":"free_text","prompt":"設問文","options":null,"context":"実績データ"}]}

typeは "scenario" または "free_text" のみ。stepは1〜5の連番。contextは必ず含めること。"""

EXPECTED_NUM_QUESTIONS = 5
VALID_TYPES = {"scenario", "free_text"}
STEP_TYPE_MAP = {1: "scenario", 2: "free_text", 3: "scenario", 4: "scenario", 5: "free_text"}


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
        result = invoke_claude(LV3_GENERATE_SYSTEM_PROMPT, user_prompt)
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
