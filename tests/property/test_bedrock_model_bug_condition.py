"""
Property test for bug condition exploration.

Spec: bedrock-model-upgrade
Property 1: Bug Condition - フォールバック定数が新モデルIDと一致する

**Validates: Requirements 2.1, 2.2**

CRITICAL: This test is EXPECTED TO FAIL on unfixed code.
Failure confirms the bug exists: MODEL_ID is still the old value.
"""

import json
from unittest.mock import patch, MagicMock

from hypothesis import given, settings, strategies as st

from backend.lib.bedrock_client import invoke_claude

EXPECTED_MODEL_ID = "global.anthropic.claude-opus-4-5-20251101-v1:0"

# Strategies: arbitrary non-empty strings for system_prompt and user_prompt
system_prompt_st = st.text(min_size=1, max_size=200)
user_prompt_st = st.text(min_size=1, max_size=200)


@settings(max_examples=50)
@given(system_prompt=system_prompt_st, user_prompt=user_prompt_st)
def test_fallback_model_id_matches_new_model(system_prompt, user_prompt):
    """
    **Validates: Requirements 2.1, 2.2**

    For any system_prompt and user_prompt, calling invoke_claude()
    with no env var BEDROCK_MODEL_ID and no model_id argument
    results in invoke_model being called with
    modelId == "global.anthropic.claude-opus-4-5-20251101-v1:0".

    On UNFIXED code this MUST FAIL because MODEL_ID is still
    "apac.anthropic.claude-opus-4-0-20250514-v1:0".
    """
    with patch("backend.lib.bedrock_client.boto3") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.invoke_model.return_value = {
            "body": MagicMock(read=MagicMock(return_value=json.dumps({"ok": True}).encode()))
        }

        invoke_claude(system_prompt, user_prompt)

        call_kwargs = mock_client.invoke_model.call_args[1]
        actual_model_id = call_kwargs["modelId"]
        assert actual_model_id == EXPECTED_MODEL_ID, (
            f"Bug confirmed: fallback MODEL_ID is '{actual_model_id}', "
            f"expected '{EXPECTED_MODEL_ID}'"
        )
