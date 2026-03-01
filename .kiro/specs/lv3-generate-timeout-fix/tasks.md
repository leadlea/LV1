# Tasks — LV3 Generate Timeout Fix

## Task 1: bedrock_client.py の read_timeout 引き上げ
- [x] 1.1 `backend/lib/bedrock_client.py` の `BotoConfig(read_timeout=28)` を `BotoConfig(read_timeout=55)` に変更する
- [x] 1.2 `tests/unit/test_bedrock_client.py` に `read_timeout=55` が設定されていることを確認するテストを追加

## Task 2: lv3_generate_handler の max_tokens 指定と stop_reason チェック追加
- [x] 2.1 `backend/handlers/lv3_generate_handler.py` の `handler` 内で `invoke_claude` 呼び出しに `max_tokens=4096` を明示指定する
- [x] 2.2 `backend/handlers/lv3_generate_handler.py` の `_parse_questions` 先頭に `stop_reason == "max_tokens"` チェックと警告ログ出力を追加する（LV2の実装を参考）

## Task 3: ユニットテスト追加
- [x] 3.1 LV3 handler の正常系テスト（`max_tokens=4096` で `invoke_claude` が呼ばれることの確認）を追加
- [x] 3.2 `_parse_questions` の `stop_reason=max_tokens` 検知テスト（警告ログ出力の確認）を追加
- [ ] 3.3 `_parse_questions` の不完全JSON（切断シミュレート）テストを追加

## Task 4: Property-Based テスト追加
- [x] 4.1 [PBT-exploration] 未修正コードの `_parse_questions` に対して、`stop_reason=max_tokens` を含む切り詰められたレスポンスを生成し、`stop_reason` チェックなしでパースに進むことを確認するテスト
- [x] 4.2 [PBT-fix] 修正後の `_parse_questions` に対して、ランダムな有効LV3シナリオJSON（5問、各フィールド有効値）を生成し、正しくパースされることを検証するテスト
- [x] 4.3 [PBT-preservation] 修正後の `_parse_questions` に対して、正常な5問JSON（`stop_reason=end_turn`）を生成し、修正前と同一の結果が返ることを検証するテスト
