# バグ修正要件ドキュメント

## はじめに

LV1とLV2を両方合格したにもかかわらず、LV3がアンロック（有効化）されないバグ。index.htmlのレベル一覧画面でLV3がグレーアウト（非表示）のままになる。

根本原因：LV2完了ハンドラー（`lv2_complete_handler.py`）がLV2専用のセッションID（`ai_levels_lv2_session`）でプログレスレコードを保存するが、ゲートハンドラー（`gate_handler.py`）およびフロントエンドのゲートロジック（`gate.js`）はLV1のセッションID（`ai_levels_session`）でプログレスを取得する。そのため、LV2の合格状態（`lv2_passed`）がLV1セッションのプログレスレコードに反映されず、LV3のアンロック条件（`lv2_passed === true`）が満たされない。

## バグ分析

### 現在の動作（不具合）

1.1 WHEN ユーザーがLV2を合格して `/lv2/complete` が呼ばれる THEN システムはLV2専用セッションID（`ai_levels_lv2_session`）のプログレスレコードに `lv2_passed: true` を保存し、LV1セッションID（`ai_levels_session`）のプログレスレコードは更新しない

1.2 WHEN ユーザーがindex.htmlに戻りレベル状態を取得する THEN システムはLV1セッションID（`ai_levels_session`）で `/levels/status` を呼び出し、そのレコードの `lv2_passed` は `false` のままであるため、LV3の `unlocked` が `false` として返される

1.3 WHEN LV3の `unlocked` が `false` として返される THEN システムはLV3カードを `hidden = true` にしてグレーアウト（非表示）のままにする

### 期待される動作（正しい動作）

2.1 WHEN ユーザーがLV2を合格して `/lv2/complete` が呼ばれる THEN システムはLV1セッションID（`ai_levels_session`）のプログレスレコードの `lv2_passed` を `true` に更新するものとする

2.2 WHEN ユーザーがindex.htmlに戻りレベル状態を取得する THEN システムはLV1セッションIDで `/levels/status` を呼び出し、`lv2_passed: true` を含むレコードを取得し、LV3の `unlocked` が `true` として返されるものとする

2.3 WHEN LV3の `unlocked` が `true` として返される THEN システムはLV3カードを表示しアクセス可能にするものとする

### 変更されない動作（リグレッション防止）

3.1 WHEN LV1を合格していないユーザーがレベル状態を取得する THEN システムはLV2を `unlocked: false` として返し続けるものとする

3.2 WHEN LV1のみ合格しLV2未合格のユーザーがレベル状態を取得する THEN システムはLV2を `unlocked: true, passed: false` として返し、LV3を `unlocked: false` として返し続けるものとする

3.3 WHEN LV1を合格して `/lv1/complete` が呼ばれる THEN システムはLV1セッションIDのプログレスレコードに `lv1_passed: true` を正しく保存し続けるものとする

3.4 WHEN LV2を不合格（`final_passed: false`）で完了する THEN システムは `lv2_passed` を `false` のままにし、LV3をアンロックしないものとする

3.5 WHEN LV3以降のレベルの合格状態が既にプログレスレコードに存在する THEN システムはそれらの値を上書きせず保持し続けるものとする
