# 実装計画: AI Levels Lv4 カリキュラム

## 概要

Lv1〜Lv3と同一アーキテクチャ（Lambda + Bedrock + DynamoDB + 3エージェントパイプライン）を活用し、Lv4固有のハンドラ・プロンプト・フロントエンドを追加する。バックエンド（Lv4ハンドラ群）→ ゲーティング拡張 → フロントエンド → デプロイ設定の順で構築する。6問構成（step範囲1〜6）、gate_handler._build_levelsは4引数化。

## タスク

- [x] 1. Lv4出題エージェント（Test_Generator）の実装
  - [x] 1.1 `backend/handlers/lv4_generate_handler.py` を実装する
    - POST /lv4/generate のハンドラ
    - Lv4カリキュラム「組織横断AI活用標準化×ガバナンス設計×持続的AI活用文化構築」のシステムプロンプト定義
    - 組織横断ガバナンスシナリオ形式で6問生成（同一組織シナリオ、ステップ1,3,5はscenario、ステップ2,4,6はfree_text）
    - 既存の `bedrock_client.py` を利用してBedrock呼び出し
    - レスポンスJSON構造の検証とフォーマット（step, type, prompt, context必須）
    - CORSヘッダー付与（Access-Control-Allow-Origin: *）
    - _Requirements: 3.1, 3.2, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 11.1, 11.4, 11.6_

  - [ ]* 1.2 Lv4生成結果の構造的正当性のプロパティテストを書く
    - **Property 1: Lv4生成結果の構造的正当性**
    - `tests/property/test_lv4_generate_properties.py` に実装
    - hypothesisで任意のセッションIDを生成し、レスポンスのJSON構造を検証
    - questions配列が6要素、各要素のstep（1〜6連番）、type（ステップ1,3,5はscenario、ステップ2,4,6はfree_text）、prompt・contextが空でない文字列であることを検証
    - **Validates: Requirements 3.1, 3.2, 4.1, 4.3, 4.4**

  - [ ]* 1.3 Lv4生成結果のランダム性のプロパティテストを書く
    - **Property 2: Lv4生成結果のランダム性**
    - `tests/property/test_lv4_generate_properties.py` に実装
    - 同一セッションIDで2回呼び出し、組織横断ガバナンスシナリオの内容（promptまたはcontext）が完全一致しないことを検証
    - **Validates: Requirements 3.3**

  - [ ]* 1.4 `tests/unit/test_lv4_generate_handler.py` のユニットテストを書く
    - 正常系: 6問の組織横断ガバナンスシナリオが正しい構造で返却されること
    - 異常系: 不正なJSONリクエストに対して400 Bad Requestが返却されること
    - Lv4固有のシステムプロンプトが使用されていることをモックで検証
    - _Requirements: 3.1, 3.2, 4.4, 11.1_

- [x] 2. Lv4採点エージェント（Grader）とレビューエージェント（Reviewer）の実装
  - [x] 2.1 `backend/lib/lv4_reviewer.py` を実装する
    - `generate_lv4_feedback(question, answer, grade_result)` 関数を実装
    - Lv4向けレビューシステムプロンプト定義（組織横断AI推進者としての具体的な改善アクションとベストプラクティス含む）
    - 既存の `bedrock_client.py` を利用してBedrock呼び出し
    - feedback, explanationフィールドを含むJSONレスポンスのパースとバリデーション
    - _Requirements: 6.1, 6.2, 6.4_

  - [x] 2.2 `backend/handlers/lv4_grade_handler.py` を実装する
    - POST /lv4/grade のハンドラ
    - Lv4固有の採点基準システムプロンプト定義（ステップごとに異なる基準: 標準化方針の網羅性・ガバナンス設計の包括性・推進体制の実効性・文化醸成プログラムの段階性・リスク管理の網羅性・ロードマップの実現可能性）
    - Bedrock呼び出しによる採点実行（score 0〜100、passed = score >= 60）
    - 採点結果をLv4 Reviewerに渡してフィードバック生成
    - 1つのAPIコールで採点+レビューを完結
    - リクエストバリデーション（session_id, step 1〜6, question, answer）
    - CORSヘッダー付与
    - _Requirements: 2.2, 5.1, 5.2, 5.3, 5.4, 6.1, 7.3, 7.4, 11.2, 11.4, 11.6_

  - [ ]* 2.3 Lv4採点結果の構造的正当性のプロパティテストを書く
    - **Property 3: Lv4採点結果の構造的正当性と合格閾値**
    - `tests/property/test_lv4_grade_properties.py` に実装
    - hypothesisで任意のLv4設問と回答を生成し、passedがbool、scoreが0〜100、passedがscore >= 60と一致することを検証
    - **Validates: Requirements 2.2, 5.1, 5.3, 7.3**

  - [ ]* 2.4 Lv4最終合否判定の正当性のプロパティテストを書く
    - **Property 4: Lv4最終合否判定の正当性**
    - `tests/property/test_lv4_grade_properties.py` に実装
    - hypothesisで任意の6つの採点結果を生成し、final_passedがtrueとなるのは全6基準のスコアが60点以上の場合のみであることを検証
    - **Validates: Requirements 2.3**

  - [ ]* 2.5 Lv4レビュー結果の構造的正当性のプロパティテストを書く
    - **Property 5: Lv4レビュー結果の構造的正当性**
    - `tests/property/test_lv4_review_properties.py` に実装
    - hypothesisで任意のLv4採点結果を生成し、feedbackとexplanationが空でない文字列であることを検証
    - **Validates: Requirements 6.1, 7.4**

  - [ ]* 2.6 `tests/unit/test_lv4_grade_handler.py` のユニットテストを書く
    - 正常系: 採点結果+フィードバックが正しい構造で返却されること
    - 異常系: step範囲外（0, 7）、空回答、不正JSONに対するエラーハンドリング
    - Lv4固有の採点基準プロンプトが使用されていることをモックで検証
    - パイプライン順序の検証（Grader → Reviewer）
    - _Requirements: 5.1, 5.3, 5.4, 6.1_

  - [ ]* 2.7 `tests/unit/test_lv4_reviewer.py` のユニットテストを書く
    - 正常系: feedback, explanationが返却されること
    - Lv4向けレビューシステムプロンプトが使用されていることをモックで検証
    - _Requirements: 6.1, 6.4_

- [x] 3. チェックポイント - Lv4エージェント実装の確認
  - 全テストが通ることを確認し、不明点があればユーザーに質問する。

- [x] 4. Lv4完了保存ハンドラの実装
  - [x] 4.1 `backend/handlers/lv4_complete_handler.py` を実装する
    - POST /lv4/complete のハンドラ
    - DynamoDBへの完了レコード保存（ai-levels-resultsテーブル、SK=RESULT#lv4）
    - ai-levels-progressテーブルのlv4_passedフラグ更新（既存のlv1_passed・lv2_passed・lv3_passedを保持）
    - 既存progressレコードをget_itemで取得し、lv1_passed・lv2_passed・lv3_passedの値を保持してput_item
    - 必須フィールドバリデーション（session_id, questions, answers, grades, final_passed）
    - DynamoDB書き込みエラー時のエラーハンドリング（エラーログ記録、リトライ可能通知）
    - CORSヘッダー付与
    - _Requirements: 8.1, 8.3, 8.4, 8.5, 9.3, 11.3, 11.6_

  - [ ]* 4.2 Lv4完了レコードの完全性のプロパティテストを書く
    - **Property 6: Lv4完了レコードの完全性**
    - `tests/property/test_lv4_complete_properties.py` に実装
    - hypothesisで任意のLv4完了データを生成し、DynamoDBモックに保存されるレコードがPK, SK(RESULT#lv4), session_id, completed_at, level("lv4"), questions, answers, grades, final_passedの全フィールドを含むことを検証
    - **Validates: Requirements 8.1, 8.3, 8.4**

  - [ ]* 4.3 Lv4途中セッションでのDB非書き込みのプロパティテストを書く
    - **Property 7: Lv4途中セッションでのDB非書き込み**
    - `tests/property/test_lv4_complete_properties.py` に実装
    - lv4_generate_handlerとlv4_grade_handlerへの任意のリクエストでDynamoDB書き込みが発生しないことを検証
    - **Validates: Requirements 8.2**

  - [ ]* 4.4 Lv4合格時のprogressフラグ更新のプロパティテストを書く
    - **Property 9: Lv4合格時のprogressフラグ更新**
    - `tests/property/test_lv4_complete_properties.py` に実装
    - hypothesisで任意のLv4完了リクエストを生成し、final_passedがtrueの場合にlv4_passedがtrueに更新され、既存のlv1_passed・lv2_passed・lv3_passedフラグが保持されることを検証
    - **Validates: Requirements 9.3**

  - [ ]* 4.5 `tests/unit/test_lv4_complete_handler.py` のユニットテストを書く
    - 正常系: 完了レコードがSK=RESULT#lv4で保存されること
    - lv1_passed・lv2_passed・lv3_passedが保持されることの具体例テスト
    - 異常系: 必須フィールド欠落、DynamoDB書き込みエラー時のエラーハンドリング
    - エッジケース: progressレコードが存在しない場合のフォールバック（lv1_passed=False、lv2_passed=False、lv3_passed=False）
    - _Requirements: 8.1, 8.3, 8.4, 8.5, 9.3_

- [x] 5. ゲーティングハンドラのLv4対応拡張（_build_levels 4引数化）
  - [x] 5.1 `backend/handlers/gate_handler.py` の `_build_levels` を4引数化する
    - `_build_levels(lv1_passed, lv2_passed, lv3_passed, lv4_passed)` に引数追加（4引数化）
    - Lv4のunlocked判定（lv3_passed=trueの場合のみ）
    - Lv4のpassed判定（lv4_passedの値に基づく）
    - handler関数でDynamoDBからlv4_passedも取得して渡す
    - _Requirements: 9.1, 9.2, 9.4, 11.5, 13.3, 14.1, 14.2, 14.3, 14.4_

  - [ ]* 5.2 Lv4ゲーティングロジックの正当性のプロパティテストを書く
    - **Property 8: Lv4ゲーティングロジックの正当性**
    - `tests/property/test_lv4_gate_properties.py` に実装
    - hypothesisで任意の4つのbool値（lv1_passed, lv2_passed, lv3_passed, lv4_passed）を生成し、Lv3未合格時にLv4がunlocked=false、Lv3合格時にLv4がunlocked=true、各レベルのpassedが対応する引数の値と一致することを検証
    - **Validates: Requirements 9.1, 9.2, 9.4, 11.5, 13.3, 14.1, 14.2, 14.3, 14.4**

  - [ ]* 5.3 `tests/unit/test_gate_handler.py` にLv4対応テストを追加する
    - Lv3合格→Lv4アンロック、Lv4合格→passed=trueの具体例テスト
    - Lv3未合格時のLv4ロック状態テスト
    - _build_levelsが4引数（lv1_passed, lv2_passed, lv3_passed, lv4_passed）を受け取ることの検証
    - _Requirements: 9.1, 9.2, 9.4, 14.1, 14.2, 14.3, 14.4_

- [x] 6. チェックポイント - Lv4バックエンド全体の確認
  - 全テストが通ることを確認し、不明点があればユーザーに質問する。

- [x] 7. フロントエンド - API拡張とindex.html更新
  - [x] 7.1 `frontend/js/api.js` にLv4用エンドポイント関数を追加する
    - `lv4Generate(sessionId)` — POST /lv4/generate 呼び出し
    - `lv4Grade(sessionId, step, question, answer)` — POST /lv4/grade 呼び出し
    - `lv4Complete(payload)` — POST /lv4/complete 呼び出し
    - _Requirements: 7.2, 7.3, 11.1, 11.2, 11.3_

  - [x] 7.2 `frontend/index.html` のLv4カードを更新する
    - 「Coming Soon」をLv4カリキュラム情報（組織横断AI活用標準化×ガバナンス設計×持続的AI活用文化構築）に更新
    - lv4.htmlへのリンクを設定
    - Lv3合格時にLv4カードを表示し「開始する」ボタンを有効化
    - 全レベルクリア時の祝福メッセージ表示エリアを追加
    - _Requirements: 9.2, 10.4, 13.1, 13.2, 13.3_

  - [x] 7.3 `frontend/js/gate.js` にLv4対応と全レベルクリア判定を追加する
    - Lv4カードの表示/非表示制御（lv3_passedに基づく）
    - `checkAllLevelsClear(levels)` 関数追加（lv1〜lv4全合格判定）
    - 全レベルクリア時の祝福メッセージ表示
    - _Requirements: 9.1, 9.2, 9.5, 13.1, 13.2_

- [x] 8. フロントエンド - Lv4テスト実行画面
  - [x] 8.1 `frontend/lv4.html` を作成する
    - Lv3のlv3.htmlと同一レイアウト構造を踏襲
    - 組織横断ガバナンスシナリオ形式に適したUI（組織状況表示エリア拡大、ガバナンス設計用の構造化テキストエリア、リスクシナリオ表示エリア）
    - 6ステップの進行状況表示（AI活用標準化戦略→ガバナンスフレームワーク設計→組織横断AI推進体制構築→AI活用文化醸成プログラム→リスク管理・コンプライアンス→中長期AI活用ロードマップ）
    - レスポンシブデザイン対応
    - _Requirements: 10.1, 10.2, 10.5_

  - [x] 8.2 `frontend/js/lv4-app.js` を作成する
    - セッション管理（sessionStorage使用、キー: ai_levels_lv4_session、UUID v4生成）
    - ページ読み込み時にLv3合格状態を検証し、未合格の場合はindex.htmlにリダイレクト
    - 出題→回答→採点→レビューの6ステップフロー制御
    - 全6ステップ完了時のみ /lv4/complete を呼び出してDB保存
    - 最終結果表示（各基準の合否・総合判定・フィードバック）
    - Lv4合格時に全レベルクリアの祝福メッセージを追加表示
    - エラー時のリトライUI
    - _Requirements: 7.1, 7.2, 7.5, 8.2, 10.2, 10.3, 13.1_

- [ ] 9. Lv4エンドポイントのCORSプロパティテスト
  - [ ]* 9.1 Lv4エンドポイントのCORSヘッダーのプロパティテストを書く
    - **Property 10: Lv4エンドポイントのCORSヘッダー**
    - `tests/property/test_lv4_cors_properties.py` に実装
    - hypothesisで任意のLv4エンドポイント（/lv4/generate, /lv4/grade, /lv4/complete）へのリクエストを生成し、レスポンスにAccess-Control-Allow-Origin: *ヘッダーが含まれることを検証
    - **Validates: Requirements 11.6**

- [x] 10. serverless.yml にLv4 Lambda関数を追加
  - [x] 10.1 `serverless.yml` にLv4用の3つのLambda関数定義を追加する
    - lv4Generate: handler=backend/handlers/lv4_generate_handler.handler, path=lv4/generate, method=post, cors=true
    - lv4Grade: handler=backend/handlers/lv4_grade_handler.handler, path=lv4/grade, method=post, cors=true
    - lv4Complete: handler=backend/handlers/lv4_complete_handler.handler, path=lv4/complete, method=post, cors=true
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
- 既存のLv1〜Lv3コード・テストは変更しない（gate_handlerの4引数化拡張を除く）
- 共通モジュール（bedrock_client.py）はそのまま利用する
- Lv4は6問構成（step範囲1〜6）、Lv3の5問構成から1問増加
- gate_handler._build_levelsは4引数化（lv1_passed, lv2_passed, lv3_passed, lv4_passed）
- Lv4合格は全レベル（Lv1〜Lv4）クリアを意味し、AI Levelsカリキュラム全体の修了となる
