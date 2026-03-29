# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - フォールバック定数が新モデルIDと一致する
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope the property to the concrete failing case: `invoke_claude()` called without `model_id` argument and without `BEDROCK_MODEL_ID` env var
  - Write a property-based test (Hypothesis) that asserts: for any `system_prompt` and `user_prompt`, calling `invoke_claude(system_prompt, user_prompt)` with no env var and no `model_id` argument results in `invoke_model` being called with `modelId == "global.anthropic.claude-opus-4-5-20251101-v1:0"`
  - Use `unittest.mock.patch` to mock `boto3` and capture the `modelId` passed to `invoke_model`
  - Run test on UNFIXED code - expect FAILURE (this confirms the bug exists: `MODEL_ID` is still `"apac.anthropic.claude-opus-4-0-20250514-v1:0"`)
  - Document counterexamples found (e.g., `invoke_claude("any_sys", "any_user")` uses `"apac.anthropic.claude-opus-4-0-20250514-v1:0"` instead of `"global.anthropic.claude-opus-4-5-20251101-v1:0"`)
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 2.1, 2.2_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - 明示的モデルID指定時の優先動作が保全される
  - **IMPORTANT**: Follow observation-first methodology
  - Observe on UNFIXED code: `invoke_claude("sys", "user", model_id="custom-model")` → `invoke_model` receives `modelId="custom-model"`
  - Observe on UNFIXED code: with env var `BEDROCK_MODEL_ID=some-model`, `invoke_claude("sys", "user")` → `invoke_model` receives `modelId` from `MODEL_ID` constant (env var is used in `feedback_generator.py`, not in `invoke_claude` directly; `invoke_claude` uses `model_id` argument or `MODEL_ID` constant)
  - Write property-based test (Hypothesis): for all non-empty `model_id` strings, calling `invoke_claude(system_prompt, user_prompt, model_id=model_id)` results in `invoke_model` being called with `modelId == model_id` (explicit argument always takes precedence over fallback constant)
  - Write property-based test: for all `system_prompt` and `user_prompt`, the body structure passed to `invoke_model` contains `anthropic_version`, `max_tokens`, `temperature`, `system`, `messages` keys regardless of model_id
  - Verify tests PASS on UNFIXED code (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Fix for MODEL_ID フォールバック定数の不整合

  - [x] 3.1 Implement the fix
    - Update `backend/lib/bedrock_client.py` L13: `MODEL_ID = "apac.anthropic.claude-opus-4-0-20250514-v1:0"` → `MODEL_ID = "global.anthropic.claude-opus-4-5-20251101-v1:0"`
    - Update `tests/unit/test_bedrock_client.py` L40: `assert call_kwargs["modelId"] == "apac.anthropic.claude-opus-4-0-20250514-v1:0"` → `assert call_kwargs["modelId"] == "global.anthropic.claude-opus-4-5-20251101-v1:0"`
    - _Bug_Condition: isBugCondition(input) where env_BEDROCK_MODEL_ID is NOT SET AND model_id_argument is None AND MODULE_CONSTANT_MODEL_ID == "apac.anthropic.claude-opus-4-0-20250514-v1:0"_
    - _Expected_Behavior: MODEL_ID == "global.anthropic.claude-opus-4-5-20251101-v1:0" and invoke_model receives this value as modelId_
    - _Preservation: Explicit model_id argument priority, retry mechanism, body structure unchanged_
    - _Requirements: 2.1, 2.2, 3.1, 3.2, 3.3, 3.4_

  - [x] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - フォールバック定数が新モデルIDと一致する
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior: `modelId == "global.anthropic.claude-opus-4-5-20251101-v1:0"`
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2_

  - [x] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - 明示的モデルID指定時の優先動作が保全される
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)

- [x] 4. Checkpoint - Ensure all tests pass
  - Run full test suite: `pytest tests/unit/test_bedrock_client.py tests/property/ -v`
  - Ensure all unit tests and property-based tests pass
  - Ensure no regressions in existing test suite
  - Ask the user if questions arise
