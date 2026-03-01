# LV4アンロックバグ修正 実装計画

## タスク

- [x] 1. バグ条件探索テストの作成
  - **Property 1: Fault Condition** - LV3合格時のLV1プログレス未更新
  - **CRITICAL**: このテストは未修正コードで失敗すること。失敗はバグの存在を確認するもの
  - **テストを修正したりコードを修正しようとしないこと**
  - **NOTE**: このテストは期待される動作をエンコードしており、修正後にパスすることでバグ修正を検証する
  - **GOAL**: バグの存在を示すカウンター例を表面化させる
  - **Scoped PBT Approach**: `final_passed=true` かつ `lv1_session_id` が有効なUUID v4で、`lv3_session_id != lv1_session_id` のケースにスコープ
  - `tests/property/test_lv3_complete_exploration.py` を作成
  - `lv3_complete_handler.py` の `_update_progress` をLV3セッションIDとLV1セッションIDで呼び出し、LV1セッションIDのプログレスレコードの `lv3_passed` が `true` に更新されることをアサート
  - 未修正コードで実行 → テスト失敗を期待（LV1プログレスが更新されないことを確認）
  - カウンター例を記録: LV1セッションIDのプログレスレコードの `lv3_passed` が `false` のまま
  - テスト作成・実行・失敗記録が完了したらタスク完了とする
  - _Requirements: 1.1, 2.1_

- [x] 2. 保持プロパティテストの作成（修正実装前に実施）
  - **Property 2: Preservation** - 既存プログレスの保全
  - **IMPORTANT**: 観察ファースト手法に従うこと
  - `tests/property/test_lv3_complete_preservation.py` を作成
  - 観察: 未修正コードでLV3セッションIDのプログレスが正しく保存されることを確認
  - 観察: 未修正コードで `final_passed: false` の場合に `lv3_passed` が `true` にならないことを確認
  - プロパティベーステスト: ランダムな既存プログレス状態（`lv1_passed`、`lv2_passed`、`lv4_passed`）で `_update_progress` を実行し、これらの値が上書きされないことを検証
  - プロパティベーステスト: `final_passed: false` の場合に `lv3_passed` が `true` に設定されないことを検証
  - プロパティベーステスト: LV3セッションIDのプログレスレコードが引き続き正しく保存されることを検証
  - 未修正コードでテスト実行 → テストパスを期待（ベースライン動作の確認）
  - テスト作成・実行・パス確認が完了したらタスク完了とする
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. フロントエンド修正: LV1セッションIDの送信追加
  - [x] 3.1 `frontend/js/lv3-app.js` の `completeSession` 関数で、`ai_levels_session` からLV1セッションIDを取得し、`ApiClient.lv3Complete` の呼び出し時に `lv1_session_id` フィールドとして追加する
    - _Requirements: 2.1_

- [x] 4. バックエンド修正: LV1プログレスの更新
  - [x] 4.1 `backend/handlers/lv3_complete_handler.py` の `_validate_body` に `lv1_session_id` のオプショナルバリデーションを追加する（存在する場合はUUID v4形式を検証）
    - _Bug_Condition: isBugCondition(input) where input.final_passed == true AND lv3_session_id != lv1_session_id AND progressTable[lv1_session_id].lv3_passed == false_
    - _Expected_Behavior: LV1セッションIDのプログレスレコードの lv3_passed を final_passed の値に更新_
    - _Preservation: 既存の lv1_passed, lv2_passed, lv4_passed は保持_
    - _Requirements: 2.1_
  - [x] 4.2 `backend/handlers/lv3_complete_handler.py` の `_update_progress` 関数にLV1セッションIDのプログレスレコード更新ロジックを追加する。既存の `lv1_passed`、`lv2_passed`、`lv4_passed` の値を保持しつつ `lv3_passed` のみ更新する
    - _Bug_Condition: isBugCondition(input) where input.final_passed == true AND lv3_session_id != lv1_session_id AND progressTable[lv1_session_id].lv3_passed == false_
    - _Expected_Behavior: LV1セッションIDのプログレスレコードの lv3_passed を final_passed の値に更新_
    - _Preservation: 既存の lv1_passed, lv2_passed, lv4_passed は保持_
    - _Requirements: 2.1, 3.3, 3.5_
  - [x] 4.3 `backend/handlers/lv3_complete_handler.py` の `handler` 関数で `lv1_session_id` をリクエストボディから取得し `_update_progress` に渡す
    - _Requirements: 2.1_

- [x] 5. ユニットテスト
  - [x] 5.1 `tests/unit/test_lv3_complete_handler.py` を作成し、LV1セッションIDのプログレスが正しく更新されるテストを追加する
    - _Requirements: 2.1_
  - [x] 5.2 `lv1_session_id` が欠落している場合のフォールバック動作テストを追加する
    - _Requirements: 2.1_
  - [x] 5.3 `final_passed: false` の場合に `lv3_passed` が `true` にならないテストを追加する
    - _Requirements: 3.4_
  - [x] 5.4 既存プログレス（`lv1_passed`、`lv2_passed`、`lv4_passed`）が上書きされないテストを追加する
    - _Requirements: 3.3, 3.5_

- [x] 6. 修正検証
  - [x] 6.1 バグ条件探索テストがパスすることを確認
    - **Property 1: Expected Behavior** - LV3合格時のLV1プログレス更新
    - **IMPORTANT**: タスク1と同じテストを再実行する。新しいテストは書かない
    - タスク1のテストは期待される動作をエンコードしている
    - テストがパスすれば、期待される動作が満たされたことを確認
    - `tests/property/test_lv3_complete_exploration.py` を実行
    - **EXPECTED OUTCOME**: テストパス（バグ修正を確認）
    - _Requirements: 2.1, 2.2_
  - [x] 6.2 保持プロパティテストが引き続きパスすることを確認
    - **Property 2: Preservation** - 既存プログレスの保全
    - **IMPORTANT**: タスク2と同じテストを再実行する。新しいテストは書かない
    - `tests/property/test_lv3_complete_preservation.py` を実行
    - **EXPECTED OUTCOME**: テストパス（リグレッションなしを確認）
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 7. チェックポイント - 全テストパスの確認
  - すべてのテストがパスすることを確認し、問題があればユーザーに確認する
