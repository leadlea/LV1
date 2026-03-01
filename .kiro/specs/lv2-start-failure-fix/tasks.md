# Tasks — LV2 Start Failure Fix

## Task 1: invoke_claude の max_tokens パラメータ化
- [x] 1.1 `backend/lib/bedrock_client.py` の `invoke_claude` に `max_tokens: int = 2048` オプション引数を追加し、body構築で使用する
- [x] 1.2 `tests/unit/test_bedrock_client.py` にデフォルト値2048のテストとカスタム値指定のテストを追加
- [x] 1.3 既存テストが全てパスすることを確認

## Task 2: lv2_generate_handler の _parse_questions バリデーション寛容化
- [x] 2.1 `_parse_questions` で `context` が `None` の場合に空文字列として扱うよう修正
- [x] 2.2 `_parse_questions` で `type` フィールドを `.strip().lower()` で正規化してからチェックするよう修正
- [x] 2.3 `_parse_questions` でBedrockレスポンスの `stop_reason` が `"max_tokens"` の場合に警告ログを出力する処理を追加
- [x] 2.4 `handler` 内の `invoke_claude` 呼び出しで `max_tokens=4096` を指定

## Task 3: フロントエンドのエラーハンドリング改善
- [x] 3.1 `frontend/js/lv2-app.js` の `start()` catch ブロックでサーバーエラーとネットワークエラーを区別し、適切なメッセージを表示する

## Task 4: ユニットテスト追加
- [x] 4.1 `_parse_questions` のcontextがnullの場合の寛容化テストを追加
- [x] 4.2 `_parse_questions` のtype正規化テスト（"Scenario", " scenario " 等）を追加
- [x] 4.3 `_parse_questions` の不完全JSON（切断シミュレート）テストを追加
- [x] 4.4 LV2 handler全体の正常系テスト（max_tokens=4096でinvoke_claudeが呼ばれることの確認）を追加

## Task 5: Property-Based テスト追加
- [x] 5.1 [PBT-exploration] 未修正コードの `_parse_questions` に対して、contextがnullやtypeの大文字小文字差異を含むランダムなLV2レスポンスを生成し、ValueErrorが発生することを確認するテスト
- [x] 5.2 [PBT-fix] 修正後の `_parse_questions` に対して、ランダムな有効LV2ケーススタディJSON（contextがnull/空文字列/有効文字列、typeの大文字小文字バリエーション）を生成し、正しくパースされることを検証するテスト
- [x] 5.3 [PBT-preservation] 修正後の `_parse_questions` に対して、正常な4問JSON（全フィールド有効値）を生成し、修正前と同一の結果が返ることを検証するテスト
