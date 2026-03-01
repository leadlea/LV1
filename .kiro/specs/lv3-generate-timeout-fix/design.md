# LV3 Generate Timeout Fix — Bugfix Design

## Overview

LV2合格後にLV3を開始すると、POST /lv3/generate が504タイムアウトエラーを返しシナリオが表示されないバグの修正設計。根本原因は3つ：(1) `lv3_generate_handler.py` が `invoke_claude()` を `max_tokens` 未指定で呼び出しデフォルトの2048が使用されるため、5問分のJSON出力が途中で切断される、(2) `bedrock_client.py` の `read_timeout=28秒` がLV3の複雑な生成に対して短すぎる、(3) LV3の `_parse_questions()` に `stop_reason` チェックがなく、切り詰められたレスポンスがそのままパースに渡される。修正は `max_tokens=4096` の明示指定、`read_timeout` の55秒への引き上げ、`stop_reason` チェックの追加の3点で構成される。

## Glossary

- **Bug_Condition (C)**: LV3シナリオ生成時に、`max_tokens` 不足によるJSON切断、または `read_timeout` 不足によるタイムアウトが発生する状態
- **Property (P)**: LV3シナリオ生成が5問の完全なJSONを返し、フロントエンドが正常にシナリオを表示できること
- **Preservation**: LV1/LV2/LV4の生成・採点・完了エンドポイント、およびリトライロジックが従来通り正常動作すること
- **invoke_claude**: `backend/lib/bedrock_client.py` のBedrock API呼び出し共通関数。全レベルの生成・採点で使用
- **_parse_questions**: `backend/handlers/lv3_generate_handler.py` のBedrockレスポンスパース・バリデーション関数
- **max_tokens**: Bedrock APIリクエストの最大出力トークン数パラメータ（現在デフォルト2048）
- **read_timeout**: boto3クライアントのHTTPレスポンス読み取りタイムアウト（現在28秒）
- **stop_reason**: Bedrockレスポンスに含まれる生成停止理由（`end_turn` = 正常完了、`max_tokens` = トークン上限到達）

## Bug Details

### Fault Condition

LV3シナリオ生成（POST /lv3/generate）を呼び出した際に、以下の条件の組み合わせでバックエンドが504エラーまたは500エラーを返す：
1. `max_tokens` 未指定（デフォルト2048）では、LV3の5問分のプロジェクトリーダーシップシナリオJSONが収まらず、レスポンスが途中で切断される
2. `read_timeout=28秒` では、LV3の複雑なプロンプト処理にBedrockが間に合わず、クライアント側でタイムアウトする
3. `_parse_questions()` に `stop_reason` チェックがないため、切り詰められたレスポンスがそのままJSONパースに渡され、パースエラー→リトライ→さらにタイムアウトの悪循環が発生する

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type {endpoint: string, bedrock_response: dict, elapsed_time: float}
  OUTPUT: boolean

  RETURN input.endpoint == "POST /lv3/generate"
         AND (
           token_truncation(input.bedrock_response)
           OR timeout_exceeded(input.elapsed_time)
           OR missing_stop_reason_check(input.bedrock_response)
         )

  WHERE token_truncation(response) :=
    response.stop_reason == "max_tokens"
    AND json output is incomplete

  WHERE timeout_exceeded(elapsed) :=
    elapsed > 28 seconds (read_timeout)
    AND bedrock has not yet returned response

  WHERE missing_stop_reason_check(response) :=
    response.stop_reason == "max_tokens"
    AND _parse_questions does not check stop_reason
    AND truncated JSON is passed directly to json.loads
END FUNCTION
```

### Examples

- ユーザーがLV2合格後にLV3を開始 → `invoke_claude()` が `max_tokens=2048`（デフォルト）で呼ばれる → 5問のシナリオJSON生成中に2048トークンに到達 → `{"questions":[{"step":1,...},{"step":2,...},{"step":3,...},{"step":4,"type":"scenario","prompt":"スキル育成` で切断 → `stop_reason` チェックなし → `json.loads` が `JSONDecodeError` → 500エラー
- Bedrockが5問の完全なJSON生成に30秒かかる → `read_timeout=28秒` でクライアント側タイムアウト → リトライ → API Gatewayの29秒制限で504エラー
- `max_tokens` 切断でパースエラー → リトライ → 再度 `max_tokens` 切断 → 再リトライ → 合計時間がAPI Gateway制限を超過 → 504エラー
- LV2の4問生成（`max_tokens=3000` 明示指定、`stop_reason` チェックあり）→ 正常に200レスポンス（バグ条件に該当しない）

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- LV1のテスト生成（POST /generate）は従来通り正常にシナリオを生成し200を返す
- LV2のケーススタディ生成（POST /lv2/generate）は `max_tokens=3000` で正常に動作する
- LV4のガバナンスシナリオ生成（POST /lv4/generate）は従来通り正常に動作する
- LV3シナリオ生成で正常にBedrockから応答が返る場合、5問のバリデーション済みシナリオをフロントエンドに返す
- `invoke_claude` のリトライロジック（ThrottlingException等の指数バックオフ）は変更しない
- `invoke_claude` のデフォルト `max_tokens=2048` は変更しない（LV3呼び出し時のみ明示指定）

**Scope:**
LV3シナリオ生成以外の全エンドポイントは本修正の影響を受けない。`read_timeout` の変更は `invoke_claude` 全体に影響するが、タイムアウトの延長は既存の正常動作に悪影響を与えない（正常レスポンスは28秒以内に返るため）。

## Hypothesized Root Cause

Based on the bug description, the most likely issues are:

1. **max_tokens未指定（主原因）**: `lv3_generate_handler.py` の `handler` が `invoke_claude()` を `max_tokens` 引数なしで呼び出しており、デフォルトの2048が使用される。LV3は5問のプロジェクトリーダーシップシナリオ（各問にstep, type, prompt, context を含み、contextが長文のプロジェクト説明）を生成するため、2048トークンでは不十分。LV2は同様の問題を `max_tokens=3000` の明示指定で解決済み。

2. **read_timeout不足（副原因）**: `bedrock_client.py` の `BotoConfig(read_timeout=28)` が全レベル共通で使用されている。LV3の5問生成はLV2の4問より複雑で時間がかかるが、28秒ではBedrockの応答を待ちきれない。API Gatewayの29秒制限と合わせて、わずか1秒のマージンしかない。Lambda timeout（60秒）に対して十分なマージンを持つ55秒に引き上げる必要がある。

3. **stop_reasonチェック欠如（副原因）**: LV2の `_parse_questions()` には `stop_reason == "max_tokens"` のチェックがあり、トークン不足による切断を早期検出できる。しかしLV3の `_parse_questions()` にはこのチェックがなく、切り詰められたJSONがそのまま `json.loads` に渡されてパースエラーとなる。早期検出できないため、無駄なリトライが発生しタイムアウトの悪循環を引き起こす。

4. **悪循環パターン**: 上記3つの問題が組み合わさることで、`max_tokens` 不足 → JSON切断 → `stop_reason` チェックなし → パースエラー → リトライ → 再度同じ `max_tokens` で失敗 → さらにリトライ → `read_timeout` 超過 → 504エラーという悪循環が発生する。

## Correctness Properties

Property 1: Fault Condition - LV3シナリオ生成の完全なJSON返却

_For any_ LV3シナリオ生成リクエスト（POST /lv3/generate）に対して、修正後の `invoke_claude` は `max_tokens=4096` でBedrockを呼び出し、`read_timeout=55秒` で十分な応答待ち時間を確保し、修正後の `_parse_questions` は `stop_reason` をチェックした上で完全なJSONレスポンスから5問のシナリオを正しくパース・バリデーションして200レスポンスを返すこと。

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

Property 2: Preservation - 既存エンドポイントの動作不変

_For any_ LV3シナリオ生成以外のリクエスト（LV1生成、LV2生成/採点/完了、LV4生成/採点/完了）に対して、修正後のコードは修正前と同一の動作を維持すること。特に `invoke_claude` のデフォルト `max_tokens=2048` は変更せず、LV2の `max_tokens=3000` も影響を受けないこと。`read_timeout` の延長は既存の正常動作に影響しないこと。

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `backend/handlers/lv3_generate_handler.py`

**Function**: `_parse_questions`, `handler`

**Specific Changes**:
1. **max_tokens明示指定**: `handler` 内の `invoke_claude` 呼び出しで `max_tokens=4096` を指定
   - 変更前: `result = invoke_claude(LV3_GENERATE_SYSTEM_PROMPT, user_prompt, model_id=FAST_MODEL_ID)`
   - 変更後: `result = invoke_claude(LV3_GENERATE_SYSTEM_PROMPT, user_prompt, max_tokens=4096, model_id=FAST_MODEL_ID)`

2. **stop_reasonチェック追加**: `_parse_questions` の先頭で `stop_reason` が `"max_tokens"` かどうかをチェックし、該当する場合は警告ログを出力する（LV2の実装と同様）
   - `stop_reason = result.get("stop_reason")`
   - `if stop_reason == "max_tokens": logger.warning("Bedrock response was truncated due to max_tokens limit")`

---

**File**: `backend/lib/bedrock_client.py`

**Function**: `invoke_claude`

**Specific Changes**:
3. **read_timeoutの引き上げ**: `BotoConfig(read_timeout=28)` を `BotoConfig(read_timeout=55)` に変更
   - Lambda timeout（60秒）に対して5秒のマージンを確保
   - API Gatewayの29秒制限はインフラ側の設定であり、本修正のスコープ外（必要に応じてserverless.ymlで調整）

## Testing Strategy

### Validation Approach

テスト戦略は2フェーズで構成される：まず未修正コードでバグを再現するカウンターエグザンプルを確認し、次に修正後のコードで正常動作と既存動作の保持を検証する。

### Exploratory Fault Condition Checking

**Goal**: 未修正コードでバグを再現し、根本原因の仮説を確認または反証する。

**Test Plan**: `_parse_questions` に対して、不完全なJSON（max_tokens切断をシミュレート）や `stop_reason=max_tokens` のレスポンスを入力し、問題の動作を確認する。

**Test Cases**:
1. **Truncated JSON Test**: max_tokens切断をシミュレートした不完全な5問JSONを `_parse_questions` に渡す（未修正コードでJSONDecodeError発生を確認）
2. **Missing stop_reason Check Test**: `stop_reason=max_tokens` のレスポンスを `_parse_questions` に渡す（未修正コードではチェックなしでそのままパースに進むことを確認）
3. **No max_tokens in invoke_claude Test**: `handler` が `invoke_claude` を `max_tokens` 未指定で呼び出すことを確認（未修正コードでデフォルト2048が使用されることを確認）

**Expected Counterexamples**:
- 不完全なJSONで `JSONDecodeError` が発生
- `stop_reason=max_tokens` が検出されずに切り詰められたJSONがパースに渡される
- `invoke_claude` がデフォルトの `max_tokens=2048` で呼ばれる

### Fix Checking

**Goal**: バグ条件に該当する全入力に対して、修正後の関数が期待通りの動作をすることを検証する。

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := handler_fixed(input)
  ASSERT invoke_claude called with max_tokens=4096
  ASSERT _parse_questions checks stop_reason before parsing
  ASSERT result is list of 5 valid question dicts
  ASSERT each question has step, type, prompt, context fields
END FOR
```

### Preservation Checking

**Goal**: バグ条件に該当しない全入力に対して、修正後の関数が修正前と同一の結果を返すことを検証する。

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT _parse_questions_original(input) == _parse_questions_fixed(input)
  ASSERT invoke_claude default max_tokens == 2048
  ASSERT LV2 invoke_claude max_tokens == 3000
END FOR
```

**Testing Approach**: Property-based testingを使用して、正常なLV3レスポンス（5問の完全なJSON）に対して修正前後で同一の結果が返ることを検証する。また、LV1/LV2/LV4のハンドラが影響を受けないことをユニットテストで確認する。

**Test Plan**: 修正前のコードで正常なJSONに対する `_parse_questions` の動作を観察し、修正後も同一の結果が返ることをproperty-based testで検証する。

**Test Cases**:
1. **Valid LV3 Response Preservation**: 正常な5問JSONに対して修正前後で同一の結果が返ることを検証
2. **LV2 Generate Preservation**: LV2生成が `max_tokens=3000` で従来通り動作することを検証
3. **invoke_claude Default Preservation**: `max_tokens` 引数なしの呼び出しでデフォルト2048が使用されることを検証

### Unit Tests

- `_parse_questions` の `stop_reason=max_tokens` 検知テスト（警告ログ出力の確認）
- `_parse_questions` の不完全JSON（切断シミュレート）テスト
- LV3 handler全体の正常系テスト（`max_tokens=4096` で `invoke_claude` が呼ばれることの確認）
- `bedrock_client.py` の `read_timeout=55` 設定テスト

### Property-Based Tests

- ランダムな有効LV3シナリオJSON（5問、各フィールド有効値）を生成し、修正後の `_parse_questions` が正しくパースすることを検証
- 正常な5問JSONに対して修正前後で同一の結果が返ることを検証（preservation）
- `stop_reason` が `end_turn` の正常レスポンスに対して、修正前後で動作が変わらないことを検証

### Integration Tests

- LV3ページ遷移→シナリオ生成→設問表示の全フロー（Bedrockモック使用）
- LV2生成が修正後も正常に動作する回帰テスト
- `read_timeout` 延長後もリトライロジックが正常に動作することの確認
