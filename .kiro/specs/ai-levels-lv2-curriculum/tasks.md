# 実装計画: AI Levels Lv2 カリキュラム

## 概要

Lv1と同一アーキテクチャ（Lambda + Bedrock + DynamoDB + 3エージェントパイプライン）を活用し、Lv2固有のハンドラ・プロンプト・フロントエンドを追加する。バックエンド（Lv2ハンドラ群）→ ゲーティング拡張 → フロントエンド → デプロイ設定の順で構築する。

## タスク

- [x] 1. Lv2出題エージェント（Test_Generator）の実装
  - [x] 1.1 `backend/handlers/lv2_generate_handler.py` を実装する
    - POST /lv2/generate のハンドラ
    - Lv2カリキュラム「業務プロセス設計×AI実行指示×成果物検証×改善サイクル」のシステムプロンプト定義
    - ケーススタディ形式で4問生成（同一業務シナリオ、ステップ1,3はscenario、ステップ2,4はfree_text）
    - 既存の `bedrock_client.py` を利用してBedrock呼び出し
    - レスポンスJSON構造の検証とフォーマット（step, type, prompt, context必須）
    - CORSヘッダー付与（Access-Control-Allow-Origin: *）
    - _Requirements: 3.1, 3.2, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 11.1, 11.4, 11.6_

  - [ ]* 1.2 Lv2生成結果の構造的正当性のプロパティテストを書く
    - **Property 1: Lv2生成結果の構造的正当性**
    - `tests/property/test_lv2_generate_properties.py` に実装
    - hypothesisで任意のセッションIDを生成し、レスポンスのJSON構造を検証
    - questions配列が4要素、各要素のstep（1〜4連番）、type（ステップ1,3はscenario、ステップ2,4はfree_text）、prompt・contextが空でない文字列であることを検証
    - **Validates: Requirements 3.1, 3.2, 4.1, 4.3, 4.4**

  - [ ]* 1.3 Lv2生成結果のランダム性のプロパティテストを書く
    - **Property 2: Lv2生成結果のランダム性**
    - `tests/property/test_lv2_generate_properties.py` に実装
    - 同一セッションIDで2回呼び出し、ケーススタディの内容（promptまたはcontext）が完全一致しないことを検証
    - **Validates: Requirements 3.3**

  - [ ]* 1.4 `tests/unit/test_lv2_generate_handler.py` のユニットテストを書く
    - 正常系: 4問のケーススタディが正しい構造で返却されること
    - 異常系: 不正なJSONリクエストに対して400 Bad Requestが返却されること
    - Lv2固有のシステムプロンプトが使用されていることをモックで検証
    - _Requirements: 3.1, 3.2, 4.4, 11.1_

- [x] 2. Lv2採点エージェント（Grader）とレビューエージェント（Reviewer）の実装
  - [x] 2.1 `backend/lib/lv2_reviewer.py` を実装する
    - `generate_lv2_feedback(question, answer, grade_result)` 関数を実装
    - Lv2向けレビューシステムプロンプト定義（実務での具体的な改善アクション含む）
    - 既存の `bedrock_client.py` を利用してBedrock呼び出し
    - feedback, explanationフィールドを含むJSONレスポンスのパースとバリデーション
    - _Requirements: 6.1, 6.2, 6.4_

  - [x] 2.2 `backend/handlers/lv2_grade_handler.py` を実装する
    - POST /lv2/grade のハンドラ
    - Lv2固有の採点基準システムプロンプト定義（ステップごとに異なる基準）
    - Bedrock呼び出しによる採点実行（score 0〜100、passed = score >= 60）
    - 採点結果をLv2 Reviewerに渡してフィードバック生成
    - 1つのAPIコールで採点+レビューを完結
    - リクエストバリデーション（session_id, step 1〜4, question, answer）
    - CORSヘッダー付与
    - _Requirements: 2.2, 5.1, 5.2, 5.3, 5.4, 6.1, 7.3, 7.4, 11.2, 11.4, 11.6_

  - [ ]* 2.3 Lv2採点結果の構造的正当性のプロパティテストを書く
    - **Property 3: Lv2採点結果の構造的正当性と合格閾値**
    - `tests/property/test_lv2_grade_properties.py` に実装
    - hypothesisで任意のLv2設問と回答を生成し、passedがbool、scoreが0〜100、passedがscore >= 60と一致することを検証
    - **Validates: Requirements 2.2, 5.1, 5.3**

  - [ ]* 2.4 Lv2最終合否判定の正当性のプロパティテストを書く
    - **Property 4: Lv2最終合否判定の正当性**
    - `tests/property/test_lv2_grade_properties.py` に実装
    - hypothesisで任意の4つの採点結果を生成し、final_passedがtrueとなるのは全4基準のスコアが60点以上の場合のみであることを検証
    - **Validates: Requirements 2.3**

  - [ ]* 2.5 Lv2レビュー結果の構造的正当性のプロパティテストを書く
    - **Property 5: Lv2レビュー結果の構造的正当性**
    - `tests/property/test_lv2_review_properties.py` に実装
    - hypothesisで任意のLv2採点結果を生成し、feedbackとexplanationが空でない文字列であることを検証
    - **Validates: Requirements 6.1**

  - [ ]* 2.6 `tests/unit/test_lv2_grade_handler.py` のユニットテストを書く
    - 正常系: 採点結果+フィードバックが正しい構造で返却されること
    - 異常系: step範囲外（0, 5）、空回答、不正JSONに対するエラーハンドリング
    - Lv2固有の採点基準プロンプトが使用されていることをモックで検証
    - パイプライン順序の検証（Grader → Reviewer）
    - _Requirements: 5.1, 5.3, 5.4, 6.1_

  - [ ]* 2.7 `tests/unit/test_lv2_reviewer.py` のユニットテストを書く
    - 正常系: feedback, explanationが返却されること
    - Lv2向けレビューシステムプロンプトが使用されていることをモックで検証
    - _Requirements: 6.1, 6.4_

- [x] 3. チェックポイント - Lv2エージェント実装の確認
  - 全テストが通ることを確認し、不明点があればユーザーに質問する。

- [x] 4. Lv2完了保存ハンドラの実装
  - [x] 4.1 `backend/handlers/lv2_complete_handler.py` を実装する
    - POST /lv2/complete のハンドラ
    - DynamoDBへの完了レコード保存（ai-levels-resultsテーブル、SK=RESULT#lv2）
    - ai-levels-progressテーブルのlv2_passedフラグ更新（既存のlv1_passedを保持）
    - 既存progressレコードをget_itemで取得し、lv1_passedの値を保持してput_item
    - 必須フィールドバリデーション（session_id, questions, answers, grades, final_passed）
    - DynamoDB書き込みエラー時のエラーハンドリング（エラーログ記録、リトライ可能通知）
    - CORSヘッダー付与
    - _Requirements: 8.1, 8.3, 8.4, 8.5, 9.3, 11.3, 11.6_

  - [ ]* 4.2 Lv2完了レコードの完全性のプロパティテストを書く
    - **Property 6: Lv2完了レコードの完全性**
    - `tests/property/test_lv2_complete_properties.py` に実装
    - hypothesisで任意のLv2完了データを生成し、DynamoDBモックに保存されるレコードがPK, SK(RESULT#lv2), session_id, completed_at, level("lv2"), questions, answers, grades, final_passedの全フィールドを含むことを検証
    - **Validates: Requirements 8.1, 8.3, 8.4**

  - [ ]* 4.3 Lv2途中セッションでのDB非書き込みのプロパティテストを書く
    - **Property 7: Lv2途中セッションでのDB非書き込み**
    - `tests/property/test_lv2_complete_properties.py` に実装
    - lv2_generate_handlerとlv2_grade_handlerへの任意のリクエストでDynamoDB書き込みが発生しないことを検証
    - **Validates: Requirements 8.2**

  - [ ]* 4.4 Lv2合格時のprogressフラグ更新のプロパティテストを書く
    - **Property 9: Lv2合格時のprogressフラグ更新**
    - `tests/property/test_lv2_complete_properties.py` に実装
    - hypothesisで任意のLv2完了リクエストを生成し、final_passedがtrueの場合にlv2_passedがtrueに更新され、既存のlv1_passedフラグが保持されることを検証
    - **Validates: Requirements 9.3**

  - [ ]* 4.5 `tests/unit/test_lv2_complete_handler.py` のユニットテストを書く
    - 正常系: 完了レコードがSK=RESULT#lv2で保存されること
    - lv1_passedが保持されることの具体例テスト
    - 異常系: 必須フィールド欠落、DynamoDB書き込みエラー時のエラーハンドリング
    - エッジケース: progressレコードが存在しない場合のフォールバック（lv1_passed=False）
    - _Requirements: 8.1, 8.3, 8.4, 8.5, 9.3_

- [x] 5. ゲーティングハンドラのLv2対応拡張
  - [x] 5.1 `backend/handlers/gate_handler.py` の `_build_levels` を拡張する
    - `_build_levels(lv1_passed, lv2_passed)` に引数追加
    - Lv2のunlocked判定（lv1_passed=trueの場合のみ）
    - Lv3のunlocked判定（lv2_passed=trueの場合のみ）
    - handler関数でDynamoDBからlv2_passedも取得して渡す
    - _Requirements: 9.1, 9.2, 9.4, 11.5_

  - [ ]* 5.2 Lv2ゲーティングロジックの正当性のプロパティテストを書く
    - **Property 8: Lv2ゲーティングロジックの正当性**
    - `tests/property/test_lv2_gate_properties.py` に実装
    - hypothesisで任意のセッション状態を生成し、Lv1未合格時にLv2がunlocked=false、Lv1合格時にLv2がunlocked=true、Lv2合格時にLv3がunlocked=trueであることを検証
    - **Validates: Requirements 9.1, 9.2, 9.4, 11.5**

  - [ ]* 5.3 `tests/unit/test_gate_handler.py` にLv2対応テストを追加する
    - Lv1合格→Lv2アンロック、Lv2合格→Lv3アンロックの具体例テスト
    - Lv1未合格時のLv2ロック状態テスト
    - _Requirements: 9.1, 9.2, 9.4_

- [x] 6. チェックポイント - Lv2バックエンド全体の確認
  - 全テストが通ることを確認し、不明点があればユーザーに質問する。

- [x] 7. フロントエンド - API拡張とindex.html更新
  - [x] 7.1 `frontend/js/api.js` にLv2用エンドポイント関数を追加する
    - `lv2Generate(sessionId)` — POST /lv2/generate 呼び出し
    - `lv2Grade(sessionId, step, question, answer)` — POST /lv2/grade 呼び出し
    - `lv2Complete(payload)` — POST /lv2/complete 呼び出し
    - _Requirements: 7.2, 7.3, 11.1, 11.2, 11.3_

  - [x] 7.2 `frontend/index.html` のLv2カードを更新する
    - 「Coming Soon」をLv2カリキュラム情報（業務プロセス設計×AI実行指示×成果物検証×改善サイクル）に更新
    - lv2.htmlへのリンクを設定
    - Lv1合格時にLv2カードを表示し「開始する」ボタンを有効化
    - _Requirements: 9.2, 10.4_

- [x] 8. フロントエンド - Lv2テスト実行画面
  - [x] 8.1 `frontend/lv2.html` を作成する
    - Lv1のlv1.htmlと同一レイアウト構造を踏襲
    - ケーススタディ形式に適したUI（シナリオ表示エリア拡大、長文回答用テキストエリア）
    - 4ステップの進行状況表示（業務プロセス設計→AI実行指示→成果物検証→改善サイクル）
    - レスポンシブデザイン対応
    - _Requirements: 10.1, 10.2, 10.5_

  - [x] 8.2 `frontend/js/lv2-app.js` を作成する
    - セッション管理（sessionStorage使用、キー: ai_levels_lv2_session、UUID v4生成）
    - ページ読み込み時にLv1合格状態を検証し、未合格の場合はindex.htmlにリダイレクト
    - 出題→回答→採点→レビューの4ステップフロー制御
    - 全4ステップ完了時のみ /lv2/complete を呼び出してDB保存
    - 最終結果表示（各基準の合否・総合判定・フィードバック）
    - エラー時のリトライUI
    - _Requirements: 7.1, 7.2, 7.5, 8.2, 10.2, 10.3_

- [x] 9. Lv2エンドポイントのCORSプロパティテスト
  - [ ]* 9.1 Lv2エンドポイントのCORSヘッダーのプロパティテストを書く
    - **Property 10: Lv2エンドポイントのCORSヘッダー**
    - `tests/property/test_lv2_cors_properties.py` に実装
    - hypothesisで任意のLv2エンドポイント（/lv2/generate, /lv2/grade, /lv2/complete）へのリクエストを生成し、レスポンスにAccess-Control-Allow-Origin: *ヘッダーが含まれることを検証
    - **Validates: Requirements 11.6**

- [x] 10. serverless.yml にLv2 Lambda関数を追加
  - [x] 10.1 `serverless.yml` にLv2用の3つのLambda関数定義を追加する
    - lv2Generate: handler=backend/handlers/lv2_generate_handler.handler, path=lv2/generate, method=post, cors=true
    - lv2Grade: handler=backend/handlers/lv2_grade_handler.handler, path=lv2/grade, method=post, cors=true
    - lv2Complete: handler=backend/handlers/lv2_complete_handler.handler, path=lv2/complete, method=post, cors=true
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
- 既存のLv1コード・テストは変更しない（gate_handlerの拡張を除く）
- 共通モジュール（bedrock_client.py）はそのまま利用する
