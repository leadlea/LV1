# LV3アンロックバグ修正 タスク

## タスク

- [x] 1. フロントエンド修正: LV1セッションIDの送信追加
  - [x] 1.1 `frontend/js/lv2-app.js` の `completeSession` 関数で、`ai_levels_session` からLV1セッションIDを取得し、`ApiClient.lv2Complete` の呼び出し時に `lv1_session_id` フィールドとして追加する
- [x] 2. バックエンド修正: LV1プログレスの更新
  - [x] 2.1 `backend/handlers/lv2_complete_handler.py` の `_validate_body` に `lv1_session_id` のオプショナルバリデーションを追加する（存在する場合はUUID v4形式を検証）
  - [x] 2.2 `backend/handlers/lv2_complete_handler.py` の `_update_progress` 関数にLV1セッションIDのプログレスレコード更新ロジックを追加する。既存の `lv1_passed`、`lv3_passed`、`lv4_passed` の値を保持しつつ `lv2_passed` のみ更新する
  - [x] 2.3 `backend/handlers/lv2_complete_handler.py` の `handler` 関数で `lv1_session_id` をリクエストボディから取得し `_update_progress` に渡す
- [x] 3. ユニットテスト
  - [x] 3.1 `tests/unit/test_lv2_complete_handler.py` を作成し、LV1セッションIDのプログレスが正しく更新されるテストを追加する
  - [x] 3.2 `lv1_session_id` が欠落している場合のフォールバック動作テストを追加する
  - [x] 3.3 `final_passed: false` の場合に `lv2_passed` が `true` にならないテストを追加する
  - [x] 3.4 既存プログレス（`lv1_passed`、`lv3_passed`、`lv4_passed`）が上書きされないテストを追加する
- [x] 4. プロパティベーステスト
  - [x] 4.1 `tests/property/test_lv2_complete_exploration.py` を作成し、未修正コードでバグを再現する探索テストを記述する（Property 1検証）
  - [x] 4.2 `tests/property/test_lv2_complete_preservation.py` を作成し、既存プログレス値が保持されることを検証するプロパティベーステストを記述する（Property 2検証）
