"""スキル定義ハンドラ - GET /selfcheck/definitions"""

import json

from backend.lib.skill_definitions import BUSINESS_LEVELS, ENGINEER_LEVELS

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "GET,OPTIONS",
}


def handler(event, context):
    """GET /selfcheck/definitions"""
    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps({
            "business": BUSINESS_LEVELS,
            "engineer": ENGINEER_LEVELS,
        }, ensure_ascii=False),
    }
