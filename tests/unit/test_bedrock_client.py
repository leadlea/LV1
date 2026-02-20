"""Unit tests for backend/lib/bedrock_client.py"""

import io
import json
from unittest.mock import patch, MagicMock

import pytest
from botocore.exceptions import ClientError

from backend.lib.bedrock_client import invoke_claude, REGION, MODEL_ID, MAX_RETRIES


def _make_bedrock_response(content: dict) -> dict:
    """Helper to build a mock Bedrock response."""
    body = MagicMock()
    body.read.return_value = json.dumps(content).encode()
    return {"body": body}


def _make_client_error(code: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": "test error"}},
        "InvokeModel",
    )


class TestInvokeClaudeRegionAndModel:
    """Requirement 9.3, 9.4: correct region and model ID."""

    def test_calls_bedrock_with_correct_region(self):
        with patch("backend.lib.bedrock_client.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            mock_client.invoke_model.return_value = _make_bedrock_response({"ok": True})

            invoke_claude("sys", "user")

            mock_boto3.client.assert_called_once_with("bedrock-runtime", region_name="ap-northeast-1")

    def test_calls_invoke_model_with_correct_model_id(self):
        with patch("backend.lib.bedrock_client.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            mock_client.invoke_model.return_value = _make_bedrock_response({"ok": True})

            invoke_claude("sys", "user")

            call_kwargs = mock_client.invoke_model.call_args[1]
            assert call_kwargs["modelId"] == "global.anthropic.claude-sonnet-4-6"

    def test_sends_correct_body_structure(self):
        with patch("backend.lib.bedrock_client.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            mock_client.invoke_model.return_value = _make_bedrock_response({"ok": True})

            invoke_claude("my system prompt", "my user prompt")

            call_kwargs = mock_client.invoke_model.call_args[1]
            body = json.loads(call_kwargs["body"])
            assert body["system"] == "my system prompt"
            assert body["messages"] == [{"role": "user", "content": [{"type": "text", "text": "my user prompt"}]}]
            assert body["anthropic_version"] == "bedrock-2023-05-31"
            assert body["max_tokens"] == 4096


class TestRetryLogic:
    """Requirement 9.3, 9.4: exponential backoff retry on retryable errors."""

    @patch("backend.lib.bedrock_client.time.sleep")
    def test_retries_on_throttling_then_succeeds(self, mock_sleep):
        with patch("backend.lib.bedrock_client.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            mock_client.invoke_model.side_effect = [
                _make_client_error("ThrottlingException"),
                _make_bedrock_response({"result": "ok"}),
            ]

            result = invoke_claude("sys", "user")

            assert result == {"result": "ok"}
            assert mock_client.invoke_model.call_count == 2
            mock_sleep.assert_called_once_with(1)  # BASE_DELAY * 2^0

    @patch("backend.lib.bedrock_client.time.sleep")
    def test_raises_after_max_retries_exhausted(self, mock_sleep):
        with patch("backend.lib.bedrock_client.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            mock_client.invoke_model.side_effect = [
                _make_client_error("ThrottlingException"),
                _make_client_error("ThrottlingException"),
                _make_client_error("ThrottlingException"),
            ]

            with pytest.raises(ClientError) as exc_info:
                invoke_claude("sys", "user")

            assert exc_info.value.response["Error"]["Code"] == "ThrottlingException"
            assert mock_client.invoke_model.call_count == MAX_RETRIES

    @patch("backend.lib.bedrock_client.time.sleep")
    def test_exponential_backoff_delays(self, mock_sleep):
        with patch("backend.lib.bedrock_client.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            mock_client.invoke_model.side_effect = [
                _make_client_error("ServiceUnavailableException"),
                _make_client_error("ServiceUnavailableException"),
                _make_bedrock_response({"ok": True}),
            ]

            invoke_claude("sys", "user")

            assert mock_sleep.call_count == 2
            mock_sleep.assert_any_call(1)   # 1 * 2^0
            mock_sleep.assert_any_call(2)   # 1 * 2^1

    def test_non_retryable_error_raises_immediately(self):
        with patch("backend.lib.bedrock_client.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            mock_client.invoke_model.side_effect = _make_client_error("ValidationException")

            with pytest.raises(ClientError) as exc_info:
                invoke_claude("sys", "user")

            assert exc_info.value.response["Error"]["Code"] == "ValidationException"
            assert mock_client.invoke_model.call_count == 1
