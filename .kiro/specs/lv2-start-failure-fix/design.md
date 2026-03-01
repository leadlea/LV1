# LV2 Start Failure Fix — Bugfix Design

## Overview

LV1クリア後にLV2ページへ遷移すると、POST /lv2/generate が失敗しLV2を開始できないバグの修正設計。主原因は `bedrock_client.py` の `max_tokens: 2048` がLV2の4問ケーススタディJSON出力に対して不十分であること、および `lv2_generate_handler.py` の `_parse_questions` バリデーションが厳格すぎてLLMレスポンスの軽微なフォーマット差異で500エラーを返すこと。修正は max_tokens の引き上げ、バリデーションの寛容化、フロントエンドのリトライUX改善の3点で構成される。

## Glossary

- **Bug_Condition (C)**: LV2ケーススタディ生成時に、Bedrockレスポンスが不完全なJSON（max_tokens不足による切断）またはLLMフォーマット差異により `_parse_questions` がValueErrorを発生させる状態
- **Property (P)**: LV2ケーススタディ生成が4問の完全なJSONを返し、フロントエンドが正常に設問を表示できること
- **Preservation**: LV1生成、LV2採点/完了、LV3/LV4の全エンドポイントが従来通り正常動作すること
- **invoke_claude**: `backend/lib/bedrock_client.py` のBedrock API呼び出し共通関数。全レベルの生成・採点で使用
- **_parse_questions**: `backend/handlers/lv2_generate_handler.py` のBedrockレスポンスパース・バリデーション関数
- **max_tokens**: Bedrock APIリクエストの最大出力トークン数パラメータ

## Bug Details

### Fault Condition

LV2ケーススタディ生成（POST /lv2/generate）を呼び出した際に、以下のいずれかの条件でバックエンドが500エラーを返す：
1. `max_tokens: 2048` ではLV2の4問分の詳細ケーススタディJSONが収まらず、レスポンスが途中で切断されて `json.loads` が `JSONDecodeError` を発生
2. LLMが返すJSONのフォーマットが期待と微妙に異なり（contextがnull、typeの表記揺れ等）、厳格なバリデーションが `ValueError` を発生

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type {endpoint: string, bedrock_response: string}
  OUTPUT: boolean

  RETURN input.endpoint == "POST /lv2/generate"
         AND (
           json_parse_fails(input.bedrock_response)
           OR validation_rejects(input.bedrock_response)
         )

  WHERE json_parse_fails(response) :=
    response is truncated due to max_tokens limit
    AND json.loads(response) raises JSONDecodeError

  WHERE validation_rejects(response) :=
    json.loads(response) succeeds
    AND (
      any question has context == null
      OR any question has type not exactly matching STEP_TYPE_MAP
      OR question count != 4
    )
END FUNCTION
```

### Examples

- ユーザーがLV1合格後にLV2ページを開く → `lv2Generate` が呼ばれる → Bedrockが4問のケーススタディを生成するが `max_tokens: 2048` で途中切断 → `{"questions":[{"step":1,...},{"step":2,...},{"step":3,...},{"step":4,"type":"free_text","prompt":"振り返り` で終了 → `json.loads` が `JSONDecodeError` → 500エラー → フロントエンドに「ケーススタディの生成に失敗しました」表示
- Bedrockが完全なJSONを返すが、ステップ3の `context` が `null` → `_parse_questions` が `ValueError("Question 2: context must be a non-empty string")` → 500エラー
- Bedrockが完全なJSONを返すが、`type` が `"Scenario"` (大文字始まり) → `_parse_questions` が `ValueError("Question 0: step 1 must be type 'scenario', got 'Scenario'")` → 500エラー
- LV1の3問生成（max_tokens: 2048で十分）→ 正常に200レスポンス（これはバグ条件に該当しない）

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- LV1のテスト・ドリル生成（POST /lv1/generate）は従来通り3問を正常に生成し200を返す
- LV2のゲートチェック（GET /levels/status）はLV1合格状態に基づきアンロック状態を正しく返す
- LV2の回答採点（POST /lv2/grade）は従来通り回答を採点しスコアとフィードバックを返す
- LV2の完了保存（POST /lv2/complete）は従来通り結果をDynamoDBに保存する
- LV3/LV4の全エンドポイント（generate/grade/complete）は従来通り正常動作する
- `invoke_claude` のリトライロジック（ThrottlingException等の指数バックオフ）は変更しない

**Scope:**
LV2ケーススタディ生成以外の全エンドポイントは本修正の影響を受けない。`invoke_claude` の `max_tokens` パラメータ化は呼び出し元が明示的に指定しない限りデフォルト値（2048）を維持するため、既存の全呼び出しに影響しない。

## Hypothesized Root Cause

Based on the bug description, the most likely issues are:

1. **max_tokens不足（主原因）**: `bedrock_client.py` の `invoke_claude` が `max_tokens: 2048` をハードコードしている。LV1は3問の簡潔なJSON（約800-1200トークン）で収まるが、LV2は4問の詳細ケーススタディ（各問にstep, type, prompt, context を含み、contextが長文の業務シナリオ説明）で2048トークンを超過する。Bedrockは `max_tokens` に達するとレスポンスを途中で切断し、不完全なJSONが返される。

2. **バリデーションの厳格さ（副原因）**: `_parse_questions` が `context` に対して `isinstance(context, str) and context.strip()` を要求しているが、LLMが `"context": null` を返すケースがある。また `type` の完全一致チェックにより、`"Scenario"` や `" scenario"` のような軽微な差異でも即座にエラーとなる。LV1の `_parse_questions` は `context` をオプショナルとして扱っており（`q.get("context")`のみ）、この差異がLV2固有の問題を引き起こしている。

3. **API Gatewayタイムアウトリスク（潜在的問題）**: Lambda timeout は60秒に設定されているが、API Gatewayのデフォルトタイムアウトは29秒。LV2の複雑なプロンプトでBedrockの応答が遅い場合、API Gatewayがタイムアウトする可能性がある。ただし、これは主原因ではなく、max_tokens修正後も残る潜在的リスク。

4. **フロントエンドのエラーハンドリング不足**: `lv2-app.js` の `start()` 関数は catch ブロックで汎用的なエラーメッセージを表示するのみで、リトライボタンは `ApiClient.showError` 経由で提供されるが、ローディング状態のまま停止する。自動リトライやより具体的なエラー情報の表示がない。

## Correctness Properties

Property 1: Fault Condition - LV2ケーススタディ生成の完全なJSON返却

_For any_ LV2ケーススタディ生成リクエスト（POST /lv2/generate）に対して、修正後の `invoke_claude` は十分な `max_tokens`（4096）でBedrockを呼び出し、修正後の `_parse_questions` は完全なJSONレスポンスから4問のケーススタディを正しくパース・バリデーションして200レスポンスを返すこと。軽微なフォーマット差異（contextがnull、typeの大文字小文字差異）があってもリカバリすること。

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

Property 2: Preservation - 既存エンドポイントの動作不変

_For any_ LV2ケーススタディ生成以外のリクエスト（LV1生成、LV2採点/完了、LV3/LV4全エンドポイント）に対して、修正後のコードは修正前と同一の動作を維持すること。特に `invoke_claude` のデフォルト `max_tokens: 2048` は変更せず、既存の全呼び出しに影響しないこと。

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `backend/lib/bedrock_client.py`

**Function**: `invoke_claude`

**Specific Changes**:
1. **max_tokensのパラメータ化**: `invoke_claude` に `max_tokens` オプション引数を追加（デフォルト値 2048 を維持）。呼び出し元が必要に応じて大きな値を指定できるようにする。
   - シグネチャ: `def invoke_claude(system_prompt: str, user_prompt: str, max_tokens: int = 2048) -> dict:`
   - body構築時に `"max_tokens": max_tokens` を使用

---

**File**: `backend/handlers/lv2_generate_handler.py`

**Function**: `_parse_questions`, `handler`

**Specific Changes**:
2. **max_tokens引き上げ**: `handler` 内の `invoke_claude` 呼び出しで `max_tokens=4096` を指定
   - `result = invoke_claude(LV2_GENERATE_SYSTEM_PROMPT, user_prompt, max_tokens=4096)`

3. **contextバリデーションの寛容化**: `_parse_questions` で `context` が `None` の場合は空文字列 `""` として扱う
   - `context = q.get("context") or ""`（Noneと空文字列の両方をハンドル）
   - contextが空文字列の場合もエラーにせず、そのまま通す

4. **typeバリデーションの正規化**: `type` フィールドを `.strip().lower()` で正規化してからチェック
   - `q_type = q.get("type", "").strip().lower()`

5. **stop_reasonチェック追加**: Bedrockレスポンスの `stop_reason` が `"max_tokens"` の場合、トークン不足による切断を検知してログに警告を出力し、適切なエラーメッセージを返す

---

**File**: `frontend/js/lv2-app.js`

**Function**: `start()`

**Specific Changes**:
6. **エラーハンドリング改善**: catch ブロックでサーバーエラー（500）とネットワークエラーを区別し、より具体的なエラーメッセージを表示。ローディング状態を適切に解除する。

## Testing Strategy

### Validation Approach

テスト戦略は2フェーズで構成される：まず未修正コードでバグを再現するカウンターエグザンプルを確認し、次に修正後のコードで正常動作と既存動作の保持を検証する。

### Exploratory Fault Condition Checking

**Goal**: 未修正コードでバグを再現し、根本原因の仮説を確認または反証する。

**Test Plan**: `_parse_questions` に対して、不完全なJSON（max_tokens切断をシミュレート）やフォーマット差異のあるJSONを入力し、ValueErrorが発生することを確認する。

**Test Cases**:
1. **Truncated JSON Test**: max_tokens切断をシミュレートした不完全なJSONを `_parse_questions` に渡す（未修正コードで失敗を確認）
2. **Null Context Test**: contextがnullのケーススタディJSONを `_parse_questions` に渡す（未修正コードで失敗を確認）
3. **Type Case Sensitivity Test**: typeが "Scenario" (大文字始まり) のJSONを `_parse_questions` に渡す（未修正コードで失敗を確認）
4. **Full Handler Test**: `invoke_claude` をモックして不完全なJSONを返し、handler全体が500を返すことを確認

**Expected Counterexamples**:
- 不完全なJSONで `JSONDecodeError` が発生
- contextがnullで `ValueError("context must be a non-empty string")` が発生
- typeの大文字小文字差異で `ValueError("must be type 'scenario'")` が発生

### Fix Checking

**Goal**: バグ条件に該当する全入力に対して、修正後の関数が期待通りの動作をすることを検証する。

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := _parse_questions_fixed(input)
  ASSERT result is list of 4 valid question dicts
  ASSERT each question has step, type, prompt, context fields
  ASSERT type values are normalized to lowercase
  ASSERT null context is converted to empty string
END FOR
```

### Preservation Checking

**Goal**: バグ条件に該当しない全入力に対して、修正後の関数が修正前と同一の結果を返すことを検証する。

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT _parse_questions_original(input) == _parse_questions_fixed(input)
  ASSERT invoke_claude_original(system, user) == invoke_claude_fixed(system, user)
END FOR
```

**Testing Approach**: Property-based testingを使用して、正常なLV2レスポンス（4問の完全なJSON）に対して修正前後で同一の結果が返ることを検証する。また、LV1/LV3/LV4のハンドラが影響を受けないことをユニットテストで確認する。

**Test Plan**: 修正前のコードで正常なJSONに対する `_parse_questions` の動作を観察し、修正後も同一の結果が返ることをproperty-based testで検証する。

**Test Cases**:
1. **Valid LV2 Response Preservation**: 正常な4問JSONに対して修正前後で同一の結果が返ることを検証
2. **LV1 Generate Preservation**: LV1生成が従来通り動作することを検証
3. **invoke_claude Default Preservation**: max_tokens引数なしの呼び出しでデフォルト2048が使用されることを検証

### Unit Tests

- `invoke_claude` の `max_tokens` パラメータ化テスト（デフォルト値2048、カスタム値4096）
- `_parse_questions` のcontextがnullの場合の寛容化テスト
- `_parse_questions` のtype正規化テスト
- `_parse_questions` のstop_reason="max_tokens"検知テスト
- LV2 handler全体の正常系テスト（max_tokens=4096でinvoke_claudeが呼ばれることの確認）
- フロントエンドのエラーハンドリング改善テスト

### Property-Based Tests

- ランダムな有効LV2ケーススタディJSON（4問、各フィールド有効値）を生成し、修正後の `_parse_questions` が正しくパースすることを検証
- contextがnull/空文字列/有効文字列のランダムな組み合わせで `_parse_questions` がエラーにならないことを検証
- typeの大文字小文字バリエーション（"scenario", "Scenario", "SCENARIO", " scenario "）で正規化が正しく動作することを検証

### Integration Tests

- LV2ページ遷移→ケーススタディ生成→設問表示の全フロー（Bedrockモック使用）
- エラー発生時のリトライフロー（500エラー→リトライボタン→再生成成功）
- LV1生成が修正後も正常に動作する回帰テスト
