# 実装計画: AI Levels Lv1 MVP

## 概要

3エージェント連動のAIカリキュラム実行システムを、バックエンド（Python 3.12 + Serverless Framework）→ フロントエンド（バニラHTML/CSS/JS）→ CI/CDの順で構築する。各ステップでテストを含め、段階的に動作確認しながら進める。

## タスク

- [x] 1. プロジェクト構造とServerless Framework設定
  - [x] 1.1 プロジェクトディレクトリ構造を作成する
    - `backend/handlers/`, `backend/lib/`, `frontend/`, `frontend/css/`, `frontend/js/`, `tests/unit/`, `tests/property/` ディレクトリを作成
    - `requirements.txt` に boto3, pytest, pytest-mock, hypothesis を記載
    - _Requirements: 9.1, 9.2_
  - [x] 1.2 serverless.ymlを作成する
    - provider設定（Python 3.12, ap-northeast-1, 環境変数）
    - IAMロール（DynamoDB, Bedrock）
    - 4つのLambda関数定義（generate, grade, complete, gate）
    - DynamoDBテーブル2つ（ai-levels-results, ai-levels-progress）のリソース定義
    - CORSを全エンドポイントで有効化
    - _Requirements: 9.1, 9.2, 7.3_

- [x] 2. Bedrock呼び出し共通モジュール
  - [x] 2.1 `backend/lib/bedrock_client.py` を実装する
    - `invoke_claude(system_prompt, user_prompt)` 関数を実装
    - リージョン: ap-northeast-1、モデルID: global.anthropic.claude-opus-4-6-v1
    - レスポンスのJSONパース処理
    - ThrottlingException等の指数バックオフリトライ（最大3回）
    - _Requirements: 1.3, 2.2, 3.2, 9.3, 9.4_
  - [x] 2.2 `backend/lib/bedrock_client.py` のユニットテストを書く
    - 正しいリージョンとモデルIDでBedrock呼び出しが行われることをモックで検証
    - リトライロジックの検証
    - _Requirements: 9.3, 9.4_

- [x] 3. 出題エージェント（Test_Generator）の実装
  - [x] 3.1 `backend/handlers/generate_handler.py` を実装する
    - POST /lv1/generate のハンドラ
    - カリキュラム「分業設計×依頼設計×品質担保×2ケース再現」のシステムプロンプト定義
    - Bedrock呼び出しによるテスト・ドリル生成
    - レスポンスJSON構造の検証とフォーマット
    - _Requirements: 1.1, 1.2, 1.4_
  - [x] 3.2 生成結果の構造的正当性のプロパティテストを書く
    - **Property 1: 生成結果の構造的正当性**
    - hypothesisで任意のセッションIDを生成し、レスポンスのJSON構造を検証
    - **Validates: Requirements 1.1, 1.4**
  - [x] 3.3 生成結果のランダム性のプロパティテストを書く
    - **Property 2: 生成結果のランダム性**
    - 同一セッションIDで2回呼び出し、結果が異なることを検証
    - **Validates: Requirements 1.2**

- [x] 4. 採点エージェント（Grader）とレビューエージェント（Reviewer）の実装
  - [x] 4.1 `backend/lib/reviewer.py` を実装する
    - `generate_feedback(question, answer, grade_result)` 関数を実装
    - Bedrock呼び出しによるフィードバック・解説生成
    - _Requirements: 3.1_
  - [x] 4.2 `backend/handlers/grade_handler.py` を実装する
    - POST /lv1/grade のハンドラ
    - Bedrock呼び出しによる採点実行
    - 採点結果をReviewerに渡してフィードバック生成
    - 1つのAPIコールで採点+レビューを完結
    - _Requirements: 2.1, 2.3, 3.1, 4.3, 4.4_
  - [x] 4.3 採点結果の構造的正当性のプロパティテストを書く
    - **Property 3: 採点結果の構造的正当性**
    - hypothesisで任意の設問・回答を生成し、passedがbool、scoreが0-100であることを検証
    - **Validates: Requirements 2.1, 2.3**
  - [x] 4.4 レビュー結果の構造的正当性のプロパティテストを書く
    - **Property 4: レビュー結果の構造的正当性**
    - hypothesisで任意の採点結果を生成し、feedbackとexplanationが空でない文字列であることを検証
    - **Validates: Requirements 3.1**

- [x] 5. チェックポイント - エージェント実装の確認
  - 全テストが通ることを確認し、不明点があればユーザーに質問する。

- [x] 6. 完了保存ハンドラの実装
  - [x] 6.1 `backend/handlers/complete_handler.py` を実装する
    - POST /lv1/complete のハンドラ
    - DynamoDBへの完了レコード保存（ai-levels-resultsテーブル）
    - ai-levels-progressテーブルのlv1_passedフラグ更新
    - 必須フィールド（session_id, questions, answers, grades, final_passed）のバリデーション
    - DynamoDB書き込みエラー時のエラーハンドリング
    - _Requirements: 5.1, 5.3, 5.4_
  - [x] 6.2 完了レコードの完全性のプロパティテストを書く
    - **Property 5: 完了レコードの完全性**
    - hypothesisで任意の完了データを生成し、DynamoDBモックに保存されるレコードの全フィールドを検証
    - **Validates: Requirements 5.1, 5.3**
  - [x] 6.3 途中セッションでのDB非書き込みのプロパティテストを書く
    - **Property 6: 途中セッションでのDB非書き込み**
    - generate_handlerとgrade_handlerへの任意のリクエストでDynamoDB書き込みが発生しないことを検証
    - **Validates: Requirements 5.2**

- [x] 7. ゲーティングハンドラの実装
  - [x] 7.1 `backend/handlers/gate_handler.py` を実装する
    - GET /levels/status のハンドラ
    - DynamoDBからセッションの進捗状態を取得
    - Lv1合格状態に基づくLv2以降のunlocked判定ロジック
    - _Requirements: 6.4_
  - [x] 7.2 ゲーティングロジックの正当性のプロパティテストを書く
    - **Property 7: ゲーティングロジックの正当性**
    - hypothesisで任意のセッション状態を生成し、Lv1未合格時にLv2以降がunlocked=falseであることを検証
    - **Validates: Requirements 6.3**

- [x] 8. チェックポイント - バックエンド全体の確認
  - 全テストが通ることを確認し、不明点があればユーザーに質問する。

- [x] 9. フロントエンド - レベル選択画面
  - [x] 9.1 `frontend/index.html` と `frontend/css/style.css` を作成する
    - レベル選択画面のHTML構造
    - レスポンシブデザイン対応のCSS
    - Lv1のみ表示、Lv2〜Lv4はロック状態で非表示
    - _Requirements: 6.1, 7.1, 7.2, 8.3, 8.4_
  - [x] 9.2 `frontend/js/api.js` を作成する
    - APIクライアント（fetch wrapper）
    - 各エンドポイントの呼び出し関数
    - エラーハンドリング（リトライボタン表示）
    - _Requirements: 7.3_
  - [x] 9.3 `frontend/js/gate.js` を作成する
    - ゲーティングロジック（レベル合格状態の取得と表示制御）
    - バックエンドAPIのレベル状態エンドポイント呼び出し
    - _Requirements: 6.1, 6.2, 6.3, 6.5_

- [x] 10. フロントエンド - Lv1カリキュラム実行画面
  - [x] 10.1 `frontend/lv1.html` を作成する
    - ステップバイステップのカリキュラムUI
    - 設問表示、回答入力フォーム、結果表示エリア
    - レスポンシブデザイン対応
    - _Requirements: 4.2, 4.5, 8.3, 8.4_
  - [x] 10.2 `frontend/js/app.js` を作成する
    - セッション管理（sessionStorage使用、UUID v4生成）
    - 出題→回答→採点→レビューのフロー制御
    - 全ステップ完了時のみ /lv1/complete を呼び出してDB保存
    - 途中離脱時はDB保存しない
    - エラー時のリトライUI
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2_

- [x] 11. チェックポイント - フロントエンド+バックエンド結合確認
  - 全テストが通ることを確認し、不明点があればユーザーに質問する。

- [x] 12. CI/CDパイプライン
  - [x] 12.1 `.github/workflows/deploy.yml` を作成する
    - mainブランチpush時のトリガー
    - バックエンドデプロイジョブ（Serverless Framework）
    - フロントエンドデプロイジョブ（S3 sync + CloudFront invalidation）
    - SERVERLESS_ACCESS_KEY, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY のシークレット使用
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [x] 13. 認証なしアクセスのプロパティテストを書く
  - **Property 8: 認証なしアクセス**
  - hypothesisで任意のLv1エンドポイントとリクエストを生成し、Authorizationヘッダーなしで正常処理されることを検証
  - **Validates: Requirements 7.3**

- [x] 14. 最終チェックポイント - 全テスト通過確認
  - 全テストが通ることを確認し、不明点があればユーザーに質問する。

## 備考

- `*` マーク付きのタスクはオプションであり、MVP高速化のためスキップ可能
- 各タスクは特定の要件にトレーサビリティを持つ
- チェックポイントで段階的に動作確認を行う
- プロパティテストは普遍的な正当性プロパティを検証し、ユニットテストは具体例とエッジケースを検証する
