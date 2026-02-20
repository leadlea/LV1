import json
import re
import time
import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

REGION = "ap-northeast-1"
MODEL_ID = "global.anthropic.claude-sonnet-4-6"
MAX_RETRIES = 3
BASE_DELAY = 1  # seconds

RETRYABLE_ERRORS = (
    "ThrottlingException",
    "ServiceUnavailableException",
    "ModelTimeoutException",
)

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", flags=re.DOTALL | re.IGNORECASE)


def strip_code_fence(text: str) -> str:
    """Remove markdown code fences (```json ... ```) from LLM output."""
    m = _CODE_FENCE_RE.match(text.strip())
    if m:
        return m.group(1).strip()
    return text.strip()


def invoke_claude(system_prompt: str, user_prompt: str) -> dict:
    """
    Bedrock RuntimeでClaude Opus 4.6を呼び出す共通関数。

    Args:
        system_prompt: システムプロンプト
        user_prompt: ユーザープロンプト

    Returns:
        Bedrockレスポンスをパースしたdict

    Raises:
        ClientError: リトライ上限超過後のBedrock呼び出しエラー
    """
    client = boto3.client("bedrock-runtime", region_name=REGION)

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "temperature": 0.7,
        "system": system_prompt,
        "messages": [{"role": "user", "content": [{"type": "text", "text": user_prompt}]}],
    })

    last_exception = None

    for attempt in range(MAX_RETRIES):
        try:
            response = client.invoke_model(
                modelId=MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=body,
            )
            result = json.loads(response["body"].read())
            return result
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in RETRYABLE_ERRORS and attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "Bedrock call failed with %s, retrying in %ss (attempt %d/%d)",
                    error_code, delay, attempt + 1, MAX_RETRIES,
                )
                time.sleep(delay)
                last_exception = e
            else:
                raise

    raise last_exception
