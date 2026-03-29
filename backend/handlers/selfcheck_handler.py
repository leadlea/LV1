"""セルフチェック送信ハンドラ - POST /selfcheck/submit"""

import json
import logging
import os
import re
from datetime import datetime, timezone

import boto3

from backend.lib.score_calculator import validate_answers, calculate_scores
from backend.lib.feedback_generator import generate_feedback

logger = logging.getLogger(__name__)

RESULTS_TABLE = os.environ.get("RESULTS_TABLE", "ai-levels-results")
UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
}


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, ensure_ascii=False),
    }


def handler(event, context):
    """POST /selfcheck/submit"""
    # Parse body
    try:
        body = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return _response(400, {"error": "Invalid JSON in request body"})

    session_id = body.get("session_id", "")
    track = body.get("track", "")
    answers = body.get("answers", {})

    # Validate session_id
    if not isinstance(session_id, str) or not UUID4_RE.match(session_id):
        return _response(400, {"error": "session_id must be a valid UUID v4"})

    # Validate track
    if track not in ("business", "engineer"):
        return _response(400, {"error": "track must be 'business' or 'engineer'"})

    # Validate answers
    if not isinstance(answers, dict):
        return _response(400, {"error": "answers must be an object"})

    validation_error = validate_answers(track, answers)
    if validation_error:
        return _response(400, {"error": validation_error})

    # Calculate scores
    scores = calculate_scores(track, answers)

    # Generate feedback (non-blocking failure)
    feedback = generate_feedback(track, answers, scores)
    feedback_unavailable = feedback is None

    # Save to DynamoDB
    completed_at = datetime.now(timezone.utc).isoformat()
    item = {
        "PK": f"SESSION#{session_id}",
        "SK": "RESULT#selfcheck",
        "session_id": session_id,
        "track": track,
        "answers": answers,
        "common_avg": str(scores["common_avg"]),
        "track_avg": str(scores["track_avg"]),
        "overall_avg": str(scores["overall_avg"]),
        "skill_level": scores["skill_level"],
        "feedback": feedback,
        "user_id": body.get("user_id"),
        "completed_at": completed_at,
    }

    try:
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(RESULTS_TABLE)
        table.put_item(Item=item)

        # Also save USER# record if user_id is provided
        user_id = body.get("user_id")
        if user_id and isinstance(user_id, str) and user_id.strip():
            user_item = {
                **item,
                "PK": f"USER#{user_id.strip()}",
                "SK": f"RESULT#{completed_at}",
            }
            table.put_item(Item=user_item)
    except Exception:
        logger.exception("Failed to save result to DynamoDB")
        return _response(500, {"error": "Failed to save result. Please retry."})

    return _response(200, {
        "session_id": session_id,
        "track": track,
        "common_avg": scores["common_avg"],
        "track_avg": scores["track_avg"],
        "overall_avg": scores["overall_avg"],
        "skill_level": scores["skill_level"],
        "feedback": feedback,
        "feedback_unavailable": feedback_unavailable,
    })
