# Bugfix Requirements Document

## Introduction

Bedrockで使用するモデルを `global.anthropic.claude-opus-4-5-20251101-v1:0` に統一する修正。`serverless.yml` の環境変数 `BEDROCK_MODEL_ID` は既に更新済みだが、`backend/lib/bedrock_client.py` のフォールバック定数 `MODEL_ID` と `tests/unit/test_bedrock_client.py` のハードコードされたアサーション値が旧モデルID（`apac.anthropic.claude-opus-4-0-20250514-v1:0`）のまま残っており、不整合が発生している。

この不整合により、環境変数 `BEDROCK_MODEL_ID` が未設定の場合にフォールバックで旧モデルが使用される問題と、テストが実態と乖離したモデルIDを検証している問題がある。

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN 環境変数 `BEDROCK_MODEL_ID` が未設定の状態で `invoke_claude()` が呼び出される THEN `bedrock_client.py` のフォールバック定数 `MODEL_ID = "apac.anthropic.claude-opus-4-0-20250514-v1:0"` が使用され、意図しない旧モデルで推論が実行される

1.2 WHEN `test_calls_invoke_model_with_correct_model_id` テストが実行される THEN アサーション値が `"apac.anthropic.claude-opus-4-0-20250514-v1:0"` のままであり、新モデルIDへの変更後にテストが実態と乖離した検証を行う

### Expected Behavior (Correct)

2.1 WHEN 環境変数 `BEDROCK_MODEL_ID` が未設定の状態で `invoke_claude()` が呼び出される THEN `bedrock_client.py` のフォールバック定数 `MODEL_ID = "global.anthropic.claude-opus-4-5-20251101-v1:0"` が使用され、新モデルで推論が実行されるものとする（SHALL）

2.2 WHEN `test_calls_invoke_model_with_correct_model_id` テストが実行される THEN アサーション値が `"global.anthropic.claude-opus-4-5-20251101-v1:0"` であり、新モデルIDとの整合性が検証されるものとする（SHALL）

### Unchanged Behavior (Regression Prevention)

3.1 WHEN 環境変数 `BEDROCK_MODEL_ID` に明示的なモデルIDが設定されている状態で `invoke_claude()` が呼び出される THEN 環境変数の値が優先的に使用される動作は変更されないものとする（SHALL CONTINUE TO）

3.2 WHEN `invoke_claude()` に `model_id` 引数が明示的に渡される THEN 引数の値が `MODEL_ID` 定数より優先される動作は変更されないものとする（SHALL CONTINUE TO）

3.3 WHEN Bedrock呼び出しでリトライ可能なエラー（ThrottlingException等）が発生する THEN 指数バックオフによるリトライ機構は変更されないものとする（SHALL CONTINUE TO）

3.4 WHEN `feedback_generator.py` が `os.environ.get("BEDROCK_MODEL_ID")` で環境変数からモデルIDを取得する THEN この取得ロジックは変更されないものとする（SHALL CONTINUE TO）
