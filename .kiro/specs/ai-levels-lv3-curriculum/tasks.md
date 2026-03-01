# 実装計画: AI Levels Lv3 カリキュラム

## 概要

Lv1・Lv2と同一アーキテクチャ（Lambda + Bedrock + DynamoDB + 3エージェントパイプライン）を活用し、Lv3固有のハンドラ・プロンプト・フロントエンドを追加する。バックエンド（Lv3ハンドラ群）→ ゲーティング拡張 → フロントエンド → デプロイ設定の順で構築する。

## タスク

- [x] 1. Lv3出題エージェント（Test_Generator）の実装
  - [x] 1.1 `backend/handlers/lv3_generate_handler.py` を実装する
    - POST /lv3/generate のハンドラ
    - Lv3カリキュラム「AI活用プロジェクトリーダーシップ×チームAI戦略策定×AI導入計画立案×スキル育成計画×ROI評価改善」のシステムプロンプト定義
    - プロジェクトリーダーシップシナリオ形式で5問生成（同一組織シナリオ、ステップ1,3,4はscenario、ステップ2,5はfree_text）
    - 既存の `bedrock_client.py` を利用してBedrock呼び出し
    - レスポンスJSON構造の検証とフォーマット（step, type, prompt, context必須）
    - CORSヘッダー付与（Access-Control-Allow-Origin: *）
    - _Requirements: 3.1, 3.2, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 11.1, 11.4, 11.6_

  - [ ]* 1.2 Lv3生成結果の構造的正当性のプロパティテストを書く
    - **Property 1: Lv3生成結果の構造的正当性**
    - `tests/property/test_lv3_generate_properties.py` に実装
    - hypothesisで任意のセッションIDを生成し、レスポンスのJSON構造を検証
    - questions配列が5要素、各要素のstep（1〜5連番）、type（ステップ1,3,4はscenario、ステップ2,5はfree_text）、prompt・contextが空でない文字列であることを検証
    - **Validates: Requirements 3.1, 3.2, 4.1, 4.3, 4.4**

  - [ ]* 1.3 Lv3生成結果のランダム性のプロパティテストを書く
    - **Property 2: Lv3生成結果のランダム性**
    - `tests/property/test_lv3_generate_properties.py` に実装
    - 同一セッションIDで2回呼び出し、プロジェクトリーダーシップシナリオの内容（promptまたはcontext）が完全一致しないことを検証
    - **Validates: Requirements 3.3**

  - [ ]* 1.4 `tests/unit/test_lv3_generate_handler.py` のユニットテストを書く
    - 正常系: 5問のプロジェクトリーダーシップシナリオが正しい構造で返却されること
    - 異常系: 不正なJSONリクエストに対して400 Bad Requestが返却されること
    - Lv3固有のシステムプロンプトが使用されていることをモックで検証
    - _Requirements: 3.1, 3.2, 4.4, 11.1_

- [x] 2. Lv3採点エージェント（Grader）とレビューエージェント（Reviewer）の実装
  - [x] 2.1 `backend/lib/lv3_reviewer.py` を実装する
    - `generate_lv3_feedback(question, answer, grade_result)` 関数を実装
    - Lv3向けレビューシステムプロンプト定義（プロジェクトリーダーとしての具体的な改善アクションとベストプラクティス含む）
    - 既存の `bedrock_client.py` を利用してBedrock呼び出し
    - feedback, explanationフィールドを含むJSONレスポンスのパースとバリデーション
    - _Requirements: 6.1, 6.2, 6.4_

  - [x] 2.2 `backend/handlers/lv3_grade_handler.py` を実装する
    - POST /lv3/grade のハンドラ
    - Lv3固有の採点基準システムプロンプト定義（ステップごとに異なる基準: プロジェクト計画の実現可能性・戦略の論理的整合性・導入計画の具体性・育成プランの段階性・ROI評価の定量性）
    - Bedrock呼び出しによる採点実行（score 0〜100、passed = score >= 60）
    - 採点結果をLv3 Reviewerに渡してフィードバック生成
    - 1つのAPIコールで採点+レビューを完結
    - リクエストバリデーション（session_id, step 1〜5, question, answer）
    - CORSヘッダー付与
    - _Requirements: 2.2, 5.1, 5.2, 5.3, 5.4, 6.1, 7.3, 7.4, 11.2, 11.4, 11.6_

  - [ ]* 2.3 Lv3採点結果の構造的正当性のプロパティテストを書く
    - **Property 3: Lv3採点結果の構造的正当性と合格閾値**
    - `tests/property/test_lv3_grade_properties.py` に実装
    - hypothesisで任意のLv3設問と回答を生成し、passedがbool、scoreが0〜100、passedがscore >= 60と一致することを検証
    - **Validates: Requirements 2.2, 5.1, 5.3**

  - [ ]* 2.4 Lv3最終合否判定の正当性のプロパティテストを書く
    - **Property 4: Lv3最終合否判定の正当性**
    - `tests/property/test_lv3_grade_properties.py` に実装
    - hypothesisで任意の5つの採点結果を生成し、final_passedがtrueとなるのは全5基準のスコアが60点以上の場合のみであることを検証
    - **Validates: Requirements 2.3**

  - [ ]* 2.5 Lv3レビュー結果の構造的正当性のプロパティテストを書く
    - **Property 5: Lv3レビュー結果の構造的正当性**
    - `tests/property/test_lv3_review_properties.py` に実装
    - hypothesisで任意のLv3採点結果を生成し、feedbackとexplanationが空でない文字列であることを検証
    - **Validates: Requirements 6.1**

  - [ ]* 2.6 `tests/unit/test_lv3_grade_handler.py` のユニットテストを書く
    - 正常系: 採点結果+フィードバックが正しい構造で返却されること
    - 異常系: step範囲外（0, 6）、空回答、不正JSONに対するエラーハンドリング
    - Lv3固有の採点基準プロンプトが使用されていることをモックで検証
    - パイプライン順序の検証（Grader → Reviewer）
    - _Requirements: 5.1, 5.3, 5.4, 6.1_

  - [ ]* 2.7 `tests/unit/test_lv3_reviewer.py` のユニットテストを書く
    - 正常系: feedback, explanationが返却されること
    - Lv3向けレビューシステムプロンプトが使用されていることをモックで検証
    - _Requirements: 6.1, 6.4_

- [x] 3. チェックポイント - Lv3エージェント実装の確認
  - 全テストが通ることを確認し、不明点があればユーザーに質問する。

- [x] 4. Lv3完了保存ハンドラの実装
  - [x] 4.1 `backend/handlers/lv3_complete_handler.py` を実装する
    - POST /lv3/complete のハンドラ
    - DynamoDBへの完了レコード保存（ai-levels-resultsテーブル、SK=RESULT#lv3）
    - ai-levels-progressテーブルのlv3_passedフラグ更新（既存のlv1_passedおよびlv2_passedを保持）
    - 既存progressレコードをget_itemで取得し、lv1_passedとlv2_passedの値を保持してput_item
    - 必須フィールドバリデーション（session_id, questions, answers, grades, final_passed）
    - DynamoDB書き込みエラー時のエラーハンドリング（エラーログ記録、リトライ可能通知）
    - CORSヘッダー付与
    - _Requirements: 8.1, 8.3, 8.4, 8.5, 9.3, 11.3, 11.6_

  - [ ]* 4.2 Lv3完了レコードの完全性のプロパティテストを書く
    - **Property 6: Lv3完了レコードの完全性**
    - `tests/property/test_lv3_complete_properties.py` に実装
    - hypothesisで任意のLv3完了データを生成し、DynamoDBモックに保存されるレコードがPK, SK(RESULT#lv3), session_id, completed_at, level("lv3"), questions, answers, grades, final_passedの全フィールドを含むことを検証
    - **Validates: Requirements 8.1, 8.3, 8.4**

  - [ ]* 4.3 Lv3途中セッションでのDB非書き込みのプロパティテストを書く
    - **Property 7: Lv3途中セッションでのDB非書き込み**
    - `tests/property/test_lv3_complete_properties.py` に実装
    - lv3_generate_handlerとlv3_grade_handlerへの任意のリクエストでDynamoDB書き込みが発生しないことを検証
    - **Validates: Requirements 8.2**

  - [ ]* 4.4 Lv3合格時のprogressフラグ更新のプロパティテストを書く
    - **Property 9: Lv3合格時のprogressフラグ更新**
    - `tests/property/test_lv3_complete_properties.py` に実装
    - hypothesisで任意のLv3完了リクエストを生成し、final_passedがtrueの場合にlv3_passedがtrueに更新され、既存のlv1_passedフラグおよびlv2_passedフラグが保持されることを検証
    - **Validates: Requirements 9.3**

  - [ ]* 4.5 `tests/unit/test_lv3_complete_handler.py` のユニットテストを書く
    - 正常系: 完了レコードがSK=RESULT#lv3で保存されること
    - lv1_passedおよびlv2_passedが保持されることの具体例テスト
    - 異常系: 必須フィールド欠落、DynamoDB書き込みエラー時のエラーハンドリング
    - エッジケース: progressレコードが存在しない場合のフォールバック（lv1_passed=False、lv2_passed=False）
    - _Requirements: 8.1, 8.3, 8.4, 8.5, 9.3_

- [x] 5. ゲーティングハンドラのLv3対応拡張
  - [x] 5.1 `backend/handlers/gate_handler.py` の `_build_levels` を拡張する
    - `_build_levels(lv1_passed, lv2_passed, lv3_passed)` に引数追加（3引数化）
    - Lv3のunlocked判定（lv2_passed=trueの場合のみ）
    - Lv4のunlocked判定（lv3_passed=trueの場合のみ）
    - handler関数でDynamoDBからlv3_passedも取得して渡す
    - _Requirements: 9.1, 9.2, 9.4, 11.5_

  - [ ]* 5.2 Lv3ゲーティングロジックの正当性のプロパティテストを書く
    - **Property 8: Lv3ゲーティングロジックの正当性**
    - `tests/property/test_lv3_gate_properties.py` に実装
    - hypothesisで任意のセッション状態を生成し、Lv2未合格時にLv3がunlocked=false、Lv2合格時にLv3がunlocked=true、Lv3合格時にLv4がunlocked=trueであることを検証
    - **Validates: Requirements 9.1, 9.2, 9.4, 11.5**

  - [ ]* 5.3 `tests/unit/test_gate_handler.py` にLv3対応テストを追加する
    - Lv2合格→Lv3アンロック、Lv3合格→Lv4アンロックの具体例テスト
    - Lv2未合格時のLv3ロック状態テスト
    - _build_levelsが3引数（lv1_passed, lv2_passed, lv3_passed）を受け取ることの検証
    - _Requirements: 9.1, 9.2, 9.4_

- [x] 6. チェックポイント - Lv3バックエンド全体の確認
  - 全テストが通ることを確認し、不明点があればユーザーに質問する。

- [x] 7. フロントエンド - API拡張とindex.html更新
  - [x] 7.1 `frontend/js/api.js` にLv3用エンドポイント関数を追加する
    - `lv3Generate(sessionId)` — POST /lv3/generate 呼び出し
    - `lv3Grade(sessionId, step, question, answer)` — POST /lv3/grade 呼び出し
    - `lv3Complete(payload)` — POST /lv3/complete 呼び出し
    - _Requirements: 7.2, 7.3, 11.1, 11.2, 11.3_

  - [x] 7.2 `frontend/index.html` のLv3カードを更新する
    - 「Coming Soon」をLv3カリキュラム情報（AI活用プロジェクトリーダーシップ×チームAI戦略策定×AI導入計画立案×スキル育成計画×ROI評価改善）に更新
    - lv3.htmlへのリンクを設定
    - Lv2合格時にLv3カードを表示し「開始する」ボタンを有効化
    - Lv4カードは「Coming Soon」のまま維持
    - _Requirements: 9.2, 10.4, 13.2, 13.3_

- [x] 8. フロントエンド - Lv3テスト実行画面
  - [x] 8.1 `frontend/lv3.html` を作成する
    - Lv2のlv2.htmlと同一レイアウト構造を踏襲
    - プロジェクトリーダーシップシナリオ形式に適したUI（組織状況表示エリア拡大、戦略記述用の構造化テキストエリア、データ表示エリア）
    - 5ステップの進行状況表示（AI活用プロジェクトリーダーシップ→チームAI戦略策定→AI導入計画立案→スキル育成計画→ROI評価改善）
    - レスポンシブデザイン対応
    - _Requirements: 10.1, 10.2, 10.5_

  - [x] 8.2 `frontend/js/lv3-app.js` を作成する
    - セッション管理（sessionStorage使用、キー: ai_levels_lv3_session、UUID v4生成）
    - ページ読み込み時にLv2合格状態を検証し、未合格の場合はindex.htmlにリダイレクト
    - 出題→回答→採点→レビューの5ステップフロー制御
    - 全5ステップ完了時のみ /lv3/complete を呼び出してDB保存
    - 最終結果表示（各基準の合否・総合判定・フィードバック）
    - エラー時のリトライUI
    - _Requirements: 7.1, 7.2, 7.5, 8.2, 10.2, 10.3_

- [ ] 9. Lv3エンドポイントのCORSプロパティテスト
  - [ ]* 9.1 Lv3エンドポイントのCORSヘッダーのプロパティテストを書く
    - **Property 10: Lv3エンドポイントのCORSヘッダー**
    - `tests/property/test_lv3_cors_properties.py` に実装
    - hypothesisで任意のLv3エンドポイント（/lv3/generate, /lv3/grade, /lv3/complete）へのリクエストを生成し、レスポンスにAccess-Control-Allow-Origin: *ヘッダーが含まれることを検証
    - **Validates: Requirements 11.6**

- [x] 10. serverless.yml にLv3 Lambda関数を追加
  - [x] 10.1 `serverless.yml` にLv3用の3つのLambda関数定義を追加する
    - lv3Generate: handler=backend/handlers/lv3_generate_handler.handler, path=lv3/generate, method=post, cors=true
    - lv3Grade: handler=backend/handlers/lv3_grade_handler.handler, path=lv3/grade, method=post, cors=true
    - lv3Complete: handler=backend/handlers/lv3_complete_handler.handler, path=lv3/complete, method=post, cors=true
    - 既存と同じDynamoDB・Bedrockのアクセス権限を付与（IAMロール変更不要）
    - _Requirements: 12.1, 12.4_

- [x] 11. チェックポイント - フロントエンド+バックエンド結合確認
  - 全テストが通ることを確認し、不明点があればユーザーに質問する。

- [x] 12. 最終チェックポイント - 全テスト通過確認
  - 全テストが通ることを確認し、不明点があればユーザーに質問する。

## 備考

- `*` マーク付きのタスクはオプションであり、MVP高速化のためスキップ可能
- 各タスクは特定の要件にトレーサビリティを持つ
- チェックポイントで段階的に動作確認を行う
- プロパティテストは普遍的な正当性プロパティを検証し、ユニットテストは具体例とエッジケースを検証する
- 既存のLv1・Lv2コード・テストは変更しない（gate_handlerの拡張を除く）
- 共通モジュール（bedrock_client.py）はそのまま利用する
