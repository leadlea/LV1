"""GET /levels/status - ゲーティングハンドラ"""

import json
import logging
import os
import re

import boto3

logger = logging.getLogger(__name__)

PROGRESS_TABLE = os.environ.get("PROGRESS_TABLE", "ai-levels-progress")

UUID_V4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}


def _get_dynamodb_resource():
    """Return a DynamoDB resource (extracted for testability)."""
    return boto3.resource("dynamodb", region_name="ap-northeast-1")


def _build_levels(lv1_passed: bool, lv2_passed: bool) -> dict:
    """Build the levels status dict based on progress."""
    return {
        "lv1": {"unlocked": True, "passed": lv1_passed},
        "lv2": {"unlocked": lv1_passed, "passed": lv2_passed},
        "lv3": {"unlocked": lv2_passed, "passed": False},
        "lv4": {"unlocked": False, "passed": False},
    }


def handler(event, context):
    """Lambda handler for GET /levels/status."""
    params = event.get("queryStringParameters") or {}
    session_id = params.get("session_id", "")

    if not session_id or not UUID_V4_PATTERN.match(session_id):
        return {
            "statusCode": 400,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": "session_id must be a valid UUID v4"}),
        }

    try:
        dynamodb = _get_dynamodb_resource()
        table = dynamodb.Table(PROGRESS_TABLE)
        resp = table.get_item(Key={"PK": f"SESSION#{session_id}", "SK": "PROGRESS"})
    except Exception as e:
        logger.error("DynamoDB read failed: %s", str(e))
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": "進捗データの取得に失敗しました。"}),
        }

    item = resp.get("Item")
    lv1_passed = item.get("lv1_passed", False) if item else False
    lv2_passed = item.get("lv2_passed", False) if item else False

    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps({"levels": _build_levels(lv1_passed, lv2_passed)}),
    }
