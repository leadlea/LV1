# Bedrock Model ID フォールバック定数の不整合修正 - Bugfix Design

## Overview

`serverless.yml` の環境変数 `BEDROCK_MODEL_ID` は `global.anthropic.claude-opus-4-5-20251101-v1:0` に更新済みだが、`backend/lib/bedrock_client.py` のフォールバック定数 `MODEL_ID` と `tests/unit/test_bedrock_client.py` のアサーション値が旧モデルID `apac.anthropic.claude-opus-4-0-20250514-v1:0` のまま残っている。

この不整合により、環境変数 `BEDROCK_MODEL_ID` が未設定の環境（ローカル開発・テスト等）でフォールバックが発動した場合に旧モデルで推論が実行される。修正は2ファイル・計2行の定数値変更のみで、ロジック変更は不要。

## Glossary

- **Bug_Condition (C)**: フォールバック定数 `MODEL_ID` が旧モデルID `apac.anthropic.claude-opus-4-0-20250514-v1:0` であること
- **Property (P)**: フォールバック定数 `MODEL_ID` が新モデルID `global.anthropic.claude-opus-4-5-20251101-v1:0` であり、`serverless.yml` と整合すること
- **Preservation**: 環境変数優先・引数優先・リトライ機構など既存の動作が変更されないこと
- **MODEL_ID**: `backend/lib/bedrock_client.py` のモジュールレベル定数。環境変数 `BEDROCK_MODEL_ID` 未設定かつ `model_id` 引数なしの場合に使用されるフォールバック値
- **invoke_claude()**: `backend/lib/bedrock_client.py` の関数。Bedrock Runtime 経由で Claude を呼び出す共通関数

## Bug Details

### Bug Condition

`serverless.yml` のモデルID更新に伴い、`bedrock_client.py` のフォールバック定数とテストのアサーション値も同期して更新すべきところ、更新漏れが発生している。

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type InvocationContext
  OUTPUT: boolean

  RETURN input.env_BEDROCK_MODEL_ID IS NOT SET
         AND input.model_id_argument IS None
         AND MODULE_CONSTANT_MODEL_ID == "apac.anthropic.claude-opus-4-0-20250514-v1:0"
END FUNCTION
```

### Examples

- `invoke_claude("sys", "user")` を環境変数 `BEDROCK_MODEL_ID` 未設定で呼び出す → 期待: `global.anthropic.claude-opus-4-5-20251101-v1:0` が使用される / 実際: `apac.anthropic.claude-opus-4-0-20250514-v1:0` が使用される
- `test_calls_invoke_model_with_correct_model_id` テスト実行 → 期待: 新モデルIDでアサート / 実際: 旧モデルIDでアサートしており、定数変更後にテストが失敗する
- `invoke_claude("sys", "user", model_id="custom-model")` → 期待通り `custom-model` が使用される（バグ条件に該当しない）
- 環境変数 `BEDROCK_MODEL_ID=some-model` 設定済みで `invoke_claude("sys", "user")` → 期待通り `some-model` が使用される（バグ条件に該当しない）

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- 環境変数 `BEDROCK_MODEL_ID` に明示的なモデルIDが設定されている場合、環境変数の値が `MODEL_ID` 定数より優先される動作
- `invoke_claude()` に `model_id` 引数が明示的に渡された場合、引数の値が優先される動作
- Bedrock 呼び出しでリトライ可能なエラー発生時の指数バックオフリトライ機構
- `feedback_generator.py` の `os.environ.get("BEDROCK_MODEL_ID")` による環境変数取得ロジック
- `invoke_claude()` のシグネチャ（引数・戻り値の型）

**Scope:**
今回の修正は定数値の変更のみ。`invoke_claude()` のロジック、`feedback_generator.py`、その他のモジュールには一切変更を加えない。

## Hypothesized Root Cause

Based on the bug description, the most likely issue is:

1. **更新漏れ（Human Error）**: `serverless.yml` の `BEDROCK_MODEL_ID` を新モデルに更新した際、`bedrock_client.py` のフォールバック定数 `MODEL_ID` と `test_bedrock_client.py` のアサーション値の同期更新が漏れた
   - `serverless.yml`: `global.anthropic.claude-opus-4-5-20251101-v1:0`（更新済み）
   - `bedrock_client.py` L13: `MODEL_ID = "apac.anthropic.claude-opus-4-0-20250514-v1:0"`（未更新）
   - `test_bedrock_client.py` L40: `assert call_kwargs["modelId"] == "apac.anthropic.claude-opus-4-0-20250514-v1:0"`（未更新）

2. **影響範囲の見落とし**: モデルIDが3箇所にハードコードされており、`serverless.yml` のみ更新して残り2箇所を見落とした

## Correctness Properties

Property 1: Bug Condition - フォールバック定数が新モデルIDと一致する

_For any_ invocation of `invoke_claude()` where the environment variable `BEDROCK_MODEL_ID` is not set and no `model_id` argument is provided, the function SHALL use `global.anthropic.claude-opus-4-5-20251101-v1:0` as the model ID for the Bedrock API call.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation - 明示的モデルID指定時の優先動作

_For any_ invocation of `invoke_claude()` where a `model_id` argument is explicitly provided OR the environment variable `BEDROCK_MODEL_ID` is set, the fixed code SHALL produce exactly the same behavior as the original code, preserving the priority logic where explicit arguments and environment variables take precedence over the fallback constant.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

## Fix Implementation

### Changes Required

Root cause は単純な更新漏れであり、定数値の変更のみで修正完了する。

**File**: `backend/lib/bedrock_client.py`

**Constant**: `MODEL_ID` (L13)

**Specific Changes**:
1. **フォールバック定数の更新**: `MODEL_ID = "apac.anthropic.claude-opus-4-0-20250514-v1:0"` → `MODEL_ID = "global.anthropic.claude-opus-4-5-20251101-v1:0"`

---

**File**: `tests/unit/test_bedrock_client.py`

**Method**: `test_calls_invoke_model_with_correct_model_id` (L40)

**Specific Changes**:
2. **アサーション値の更新**: `assert call_kwargs["modelId"] == "apac.anthropic.claude-opus-4-0-20250514-v1:0"` → `assert call_kwargs["modelId"] == "global.anthropic.claude-opus-4-5-20251101-v1:0"`

## Testing Strategy

### Validation Approach

修正が定数値の変更のみであるため、テスト戦略はシンプル。既存テストスイートの PASS 確認を主軸とし、プロパティベーステストでフォールバック・優先順位ロジックの保全を検証する。

### Exploratory Bug Condition Checking

**Goal**: 修正前のコードでバグ条件を再現し、旧モデルIDがフォールバックとして使用されることを確認する。

**Test Plan**: `invoke_claude()` を環境変数未設定・`model_id` 引数なしで呼び出し、`invoke_model` に渡される `modelId` が旧モデルIDであることを確認する。

**Test Cases**:
1. **フォールバック定数値テスト**: `MODEL_ID` 定数が `"apac.anthropic.claude-opus-4-0-20250514-v1:0"` であることを確認（修正前コードで PASS → バグ再現）
2. **invoke_claude デフォルト呼び出しテスト**: 環境変数なし・引数なしで `invoke_claude()` を呼び出し、`modelId` が旧値であることを確認（修正前コードで PASS → バグ再現）

**Expected Counterexamples**:
- `MODEL_ID` が `"global.anthropic.claude-opus-4-5-20251101-v1:0"` でないことが検出される
- `serverless.yml` の値と `MODEL_ID` の値が不一致であることが検出される

### Fix Checking

**Goal**: 修正後、フォールバック定数が新モデルIDと一致することを検証する。

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := invoke_claude_fixed(input.system_prompt, input.user_prompt)
  ASSERT modelId_used == "global.anthropic.claude-opus-4-5-20251101-v1:0"
END FOR
```

### Preservation Checking

**Goal**: 修正後、明示的なモデルID指定時の優先動作が変更されていないことを検証する。

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT invoke_claude_original(input) == invoke_claude_fixed(input)
END FOR
```

**Testing Approach**: プロパティベーステストにより、任意のモデルID文字列を `model_id` 引数として渡した場合に常にその値が優先されることを検証する。これにより、定数変更がフォールバック以外の動作に影響しないことを保証する。

**Test Cases**:
1. **model_id 引数優先テスト**: 任意の `model_id` 引数を渡した場合、`invoke_model` の `modelId` がその値であることを検証
2. **リトライ機構保全テスト**: 既存のリトライテスト（`TestRetryLogic`）が全て PASS することを確認
3. **Body構造保全テスト**: `invoke_model` に渡される body の構造（`anthropic_version`, `max_tokens`, `system`, `messages`）が変更されていないことを確認

### Unit Tests

- `MODEL_ID` 定数が `"global.anthropic.claude-opus-4-5-20251101-v1:0"` であることを直接アサート
- `test_calls_invoke_model_with_correct_model_id` が新モデルIDで PASS することを確認
- 既存テストスイート全体の PASS 確認（リグレッションなし）

### Property-Based Tests

- 任意の `model_id` 文字列を引数に渡した場合、`invoke_model` の `modelId` がその値と一致することを検証（Preservation Property）
- 任意の `system_prompt` / `user_prompt` に対して、引数なし・環境変数なしの場合に `MODEL_ID` 定数が使用されることを検証（Fix Property）

### Integration Tests

- 既存の `test_bedrock_client.py` テストスイート全体の実行・PASS 確認
- `feedback_generator.py` 関連テストの PASS 確認（変更なしの確認）
