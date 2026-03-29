"""
Property tests for preservation of existing behavior.

Spec: bedrock-model-upgrade
Property 2: Preservation - 明示的モデルID指定時の優先動作が保全される

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

These tests MUST PASS on UNFIXED code.
They confirm baseline behavior that must be preserved after the fix.
"""

import json
from unittest.mock import patch, MagicMock

from hypothesis import given, settings, strategies as st

from backend.lib.bedrock_client import invoke_claude


# --- Strategies ---
# Non-empty model_id strings (printable, reasonable length)
model_id_st = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
    min_size=1,
    max_size=100,
)
system_prompt_st = st.text(min_size=1, max_size=200)
user_prompt_st = st.text(min_size=1, max_size=200)


@settings(max_examples=50)
@given(
    system_prompt=system_prompt_st,
    user_prompt=user_prompt_st,
    model_id=model_id_st,
)
def test_explicit_model_id_always_takes_precedence(system_prompt, user_prompt, model_id):
    """
    **Validates: Requirements 3.1, 3.2**

    For any non-empty model_id string, calling
    invoke_claude(system_prompt, user_prompt, model_id=model_id)
    results in invoke_model being called with modelId == model_id.
    Explicit argument always takes precedence over fallback constant.
    """
    with patch("backend.lib.bedrock_client.boto3") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.invoke_model.return_value = {
            "body": MagicMock(
                read=MagicMock(return_value=json.dumps({"ok": True}).encode())
            )
        }

        invoke_claude(system_prompt, user_prompt, model_id=model_id)

        call_kwargs = mock_client.invoke_model.call_args[1]
        assert call_kwargs["modelId"] == model_id, (
            f"Expected modelId='{model_id}', got '{call_kwargs['modelId']}'. "
            f"Explicit model_id argument must always take precedence."
        )


@settings(max_examples=50)
@given(
    system_prompt=system_prompt_st,
    user_prompt=user_prompt_st,
    model_id=st.one_of(st.none(), model_id_st),
)
def test_body_structure_contains_required_keys(system_prompt, user_prompt, model_id):
    """
    **Validates: Requirements 3.3, 3.4**

    For any system_prompt and user_prompt, the body structure passed to
    invoke_model contains anthropic_version, max_tokens, temperature,
    system, and messages keys regardless of model_id.
    """
    with patch("backend.lib.bedrock_client.boto3") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.invoke_model.return_value = {
            "body": MagicMock(
                read=MagicMock(return_value=json.dumps({"ok": True}).encode())
            )
        }

        if model_id is not None:
            invoke_claude(system_prompt, user_prompt, model_id=model_id)
        else:
            invoke_claude(system_prompt, user_prompt)

        call_kwargs = mock_client.invoke_model.call_args[1]
        body = json.loads(call_kwargs["body"])

        required_keys = {"anthropic_version", "max_tokens", "temperature", "system", "messages"}
        missing = required_keys - set(body.keys())
        assert not missing, (
            f"Body is missing required keys: {missing}. "
            f"Body keys: {set(body.keys())}"
        )

        # Verify values are structurally correct
        assert body["system"] == system_prompt
        assert isinstance(body["messages"], list)
        assert len(body["messages"]) == 1
        assert body["messages"][0]["role"] == "user"
