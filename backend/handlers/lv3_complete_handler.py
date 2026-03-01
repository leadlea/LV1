"""POST /lv3/complete - Lv3完了レコード保存ハンドラ"""

import json
import logging
import os
import re
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

RESULTS_TABLE = os.environ.get("RESULTS_TABLE", "ai-levels-results")
PROGRESS_TABLE = os.environ.get("PROGRESS_TABLE", "ai-levels-progress")

UUID_V4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

REQUIRED_FIELDS = ("session_id", "questions", "answers", "grades", "final_passed")


def _validate_body(body: dict) -> str | None:
    """Validate request body. Returns error message or None if valid."""
    for field in REQUIRED_FIELDS:
        if field not in body:
            return f"{field} is required"

    session_id = body["session_id"]
    if not isinstance(session_id, str) or not UUID_V4_PATTERN.match(session_id):
        return "session_id must be a valid UUID v4"

    if not isinstance(body["questions"], list) or len(body["questions"]) == 0:
        return "questions must be a non-empty list"

    if not isinstance(body["answers"], list) or len(body["answers"]) == 0:
        return "answers must be a non-empty list"

    if not isinstance(body["grades"], list) or len(body["grades"]) == 0:
        return "grades must be a non-empty list"

    if not isinstance(body["final_passed"], bool):
        return "final_passed must be a boolean"

    return None


def _get_dynamodb_resource():
    """Return a DynamoDB resource (extracted for testability)."""
    return boto3.resource("dynamodb", region_name="ap-northeast-1")


def _save_result(dynamodb, session_id: str, body: dict, completed_at: str) -> None:
    """Save the completion record to ai-levels-results table."""
    table = dynamodb.Table(RESULTS_TABLE)
    total_score = 0
    for g in body["grades"]:
        if isinstance(g, dict) and isinstance(g.get("score"), (int, float)):
            total_score += g["score"]

    table.put_item(Item={
        "PK": f"SESSION#{session_id}",
        "SK": "RESULT#lv3",
        "session_id": session_id,
        "level": "lv3",
        "questions": body["questions"],
        "answers": body["answers"],
        "grades": body["grades"],
        "final_passed": body["final_passed"],
        "total_score": total_score,
        "completed_at": completed_at,
    })


def _update_progress(dynamodb, session_id: str, final_passed: bool, updated_at: str):
    """Update the lv3_passed flag while preserving existing progress."""
    table = dynamodb.Table(PROGRESS_TABLE)
    # Get existing record to preserve lv1_passed and lv2_passed
    resp = table.get_item(Key={"PK": f"SESSION#{session_id}", "SK": "PROGRESS"})
    existing = resp.get("Item", {})
    table.put_item(Item={
        "PK": f"SESSION#{session_id}",
        "SK": "PROGRESS",
        "session_id": session_id,
        "lv1_passed": existing.get("lv1_passed", False),
        "lv2_passed": existing.get("lv2_passed", False),
        "lv3_passed": final_passed,
        "lv4_passed": False,
        "updated_at": updated_at,
    })


def handler(event, context):
    """Lambda handler for POST /lv3/complete."""
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "Invalid JSON in request body"}),
        }

    error = _validate_body(body)
    if error:
        return {
            "statusCode": 400,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": error}),
        }

    session_id = body["session_id"]
    now = datetime.now(timezone.utc).isoformat()

    try:
        dynamodb = _get_dynamodb_resource()
        _save_result(dynamodb, session_id, body, now)
        _update_progress(dynamodb, session_id, body["final_passed"], now)
    except ClientError as e:
        logger.error("DynamoDB write failed: %s", str(e))
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "error": "データの保存に失敗しました。リトライしてください。"
            }),
        }

    return {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": json.dumps({
            "saved": True,
            "record_id": f"SESSION#{session_id}",
        }),
    }
