"""履歴取得ハンドラ - GET /selfcheck/history"""

import json
import logging
import os
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

logger = logging.getLogger(__name__)

RESULTS_TABLE = os.environ.get("RESULTS_TABLE", "ai-levels-results")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
}


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def _response(status_code: int, body) -> dict:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body, ensure_ascii=False, cls=DecimalEncoder),
    }


def handler(event, context):
    """GET /selfcheck/history?user_id=xxx"""
    params = event.get("queryStringParameters") or {}
    user_id = params.get("user_id", "").strip()

    if not user_id:
        return _response(400, {"error": "user_id is required"})

    try:
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(RESULTS_TABLE)
        resp = table.query(
            KeyConditionExpression=Key("PK").eq(f"USER#{user_id}") & Key("SK").begins_with("RESULT#"),
            ScanIndexForward=True,  # oldest first
        )
        items = resp.get("Items", [])

        results = []
        for item in items:
            results.append({
                "completed_at": item.get("completed_at"),
                "track": item.get("track"),
                "common_avg": item.get("common_avg"),
                "track_avg": item.get("track_avg"),
                "overall_avg": item.get("overall_avg"),
                "skill_level": item.get("skill_level"),
                "feedback": item.get("feedback"),
            })

        return _response(200, {"user_id": user_id, "results": results})
    except Exception:
        logger.exception("Failed to query history")
        return _response(500, {"error": "Failed to retrieve history"})
