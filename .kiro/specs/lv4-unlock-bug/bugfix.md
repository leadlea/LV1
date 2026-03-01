# バグ修正要件ドキュメント

## はじめに

LV3を全問合格したにもかかわらず、LV4の試験ボタンが無効のままで進めないバグ。index.htmlのレベル一覧画面でLV4がグレーアウト（非表示）のままになる。LV2→LV3アンロックバグ（lv3-unlock-bug）と全く同じパターンの問題。

根本原因：LV3完了ハンドラー（`lv3_complete_handler.py`）がLV3専用のセッションID（`ai_levels_lv3_session`）でプログレスレコードを保存するが、ゲートハンドラー（`gate_handler.py`）およびフロントエンドのゲートロジック（`gate.js`）はLV1のセッションID（`ai_levels_session`）でプログレスを取得する。そのため、LV3の合格状態（`lv3_passed`）がLV1セッションのプログレスレコードに反映されず、LV4のアンロック条件（`lv3_passed === true`）が満たされない。

## バグ分析

### 現在の動作（不具合）

1.1 WHEN ユーザーがLV3を合格して `/lv3/complete` が呼ばれる THEN システムはLV3専用セッションID（`ai_levels_lv3_session`）のプログレスレコードに `lv3_passed: true` を保存し、LV1セッションID（`ai_levels_session`）のプログレスレコードは更新しない

1.2 WHEN ユーザーがindex.htmlに戻りレベル状態を取得する THEN システムはLV1セッションID（`ai_levels_session`）で `/levels/status` を呼び出し、そのレコードの `lv3_passed` は `false` のままであるため、LV4の `unlocked` が `false` として返される

1.3 WHEN LV4の `unlocked` が `false` として返される THEN システムはLV4カードを `hidden = true` にしてグレーアウト（非表示）のままにする

### 期待される動作（正しい動作）

2.1 WHEN ユーザーがLV3を合格して `/lv3/complete` が呼ばれる THEN システムはLV1セッションID（`ai_levels_session`）のプログレスレコードの `lv3_passed` を `true` に更新するものとする

2.2 WHEN ユーザーがindex.htmlに戻りレベル状態を取得する THEN システムはLV1セッションIDで `/levels/status` を呼び出し、`lv3_passed: true` を含むレコードを取得し、LV4の `unlocked` が `true` として返されるものとする

2.3 WHEN LV4の `unlocked` が `true` として返される THEN システムはLV4カードを表示しアクセス可能にするものとする

### 変更されない動作（リグレッション防止）

3.1 WHEN LV1・LV2を合格していないユーザーがレベル状態を取得する THEN システムはLV3を `unlocked: false` として返し続けるものとする

3.2 WHEN LV1・LV2のみ合格しLV3未合格のユーザーがレベル状態を取得する THEN システムはLV3を `unlocked: true, passed: false` として返し、LV4を `unlocked: false` として返し続けるものとする

3.3 WHEN LV1・LV2を合格して `/lv1/complete` や `/lv2/complete` が呼ばれる THEN システムはLV1セッションIDのプログレスレコードに `lv1_passed: true` および `lv2_passed: true` を正しく保存し続けるものとする

3.4 WHEN LV3を不合格（`final_passed: false`）で完了する THEN システムは `lv3_passed` を `false` のままにし、LV4をアンロックしないものとする

3.5 WHEN LV4の合格状態が既にプログレスレコードに存在する THEN システムはその値を上書きせず保持し続けるものとする
