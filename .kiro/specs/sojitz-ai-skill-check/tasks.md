# Implementation Plan: AIスキルセルフチェックシステム

## Overview

既存のAI Levels（Lv1〜Lv4カリキュラム）を全面リプレイスし、AIスキルセルフチェック＋スキル定義参照システムに置き換える。既存AWSリソース（DynamoDB、S3、CloudFront、API Gateway）を再利用し、Lambda関数・フロントエンド・テストを全面書き替える。

実装言語: バックエンド Python 3.12 / フロントエンド HTML + CSS + Vanilla JS

## Tasks

- [x] 1. 既存Lv1〜Lv4ファイルの削除とプロジェクト構造整理
  - [x] 1.1 既存バックエンドハンドラの削除
    - `backend/handlers/generate_handler.py`, `grade_handler.py`, `complete_handler.py`, `gate_handler.py` を削除
    - `backend/handlers/lv2_generate_handler.py`, `lv2_grade_handler.py`, `lv2_complete_handler.py` を削除
    - `backend/handlers/lv3_generate_handler.py`, `lv3_grade_handler.py`, `lv3_complete_handler.py` を削除
    - `backend/handlers/lv4_generate_handler.py`, `lv4_grade_handler.py`, `lv4_complete_handler.py` を削除
    - _Requirements: 設計書「既存のLv1〜Lv4関連Lambda関数を全て削除」_
  - [x] 1.2 既存バックエンドライブラリの削除
    - `backend/lib/reviewer.py`, `lv2_reviewer.py`, `lv3_reviewer.py`, `lv4_reviewer.py`, `threshold_resolver.py` を削除
    - `backend/lib/bedrock_client.py` は保持（変更不要）
    - _Requirements: 設計書「bedrock_client.pyはそのまま流用」_
  - [x] 1.3 既存フロントエンドファイルの削除
    - `frontend/lv1.html`, `lv2.html`, `lv3.html`, `lv4.html` を削除
    - `frontend/js/app.js`, `lv2-app.js`, `lv3-app.js`, `lv4-app.js`, `gate.js` を削除
    - _Requirements: 設計書「フロントエンドを全面書き替え」_
  - [x] 1.4 既存テストファイルの削除
    - `tests/unit/` 配下の既存テスト（test_bedrock_client.py以外）を全て削除
    - `tests/property/` 配下の既存テストを全て削除
    - _Requirements: 設計書「テストも全面書き替え」_

- [x] 2. バックエンドコアモジュール実装
  - [x] 2.1 セルフチェック項目定義の実装（check_items.py）
    - `backend/lib/check_items.py` を作成
    - COMMON_ITEMS（共通6項目）、BUSINESS_ITEMS（ビジネス追加6項目）、ENGINEER_ITEMS（エンジニア追加6項目）を定義
    - 各項目はid（common_1〜6, biz_1〜6, eng_1〜6）とtextを持つ辞書のリスト
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  - [x] 2.2 スキル定義データの実装（skill_definitions.py）
    - `backend/lib/skill_definitions.py` を作成
    - BUSINESS_LEVELS（Lv1〜Lv5: 安全利用の基本者〜変革リーダー）を定義
    - ENGINEER_LEVELS（Lv1〜Lv5: エントリー〜社内ハイエンド）を定義
    - _Requirements: 7.1, 7.2_
  - [x] 2.3 スコア集計・レベル判定モジュールの実装（score_calculator.py）
    - `backend/lib/score_calculator.py` を作成
    - `validate_answers(track, answers)`: 回答データのバリデーション（項目数12、各値0-4整数、項目IDとトラックの一致）
    - `calculate_scores(track, answers)`: common_avg, track_avg, overall_avg（均等加重50:50）, skill_levelを算出
    - `determine_level(overall_avg)`: 閾値マッピングでLv1〜Lv5を判定
    - _Requirements: 3.3, 3.4, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_
  - [x]* 2.4 スコア集計のプロパティテスト（Property 1: スコア集計の数学的正当性）
    - **Property 1: スコア集計の数学的正当性**
    - hypothesisで任意の有効回答データを生成し、common_avg・track_avg・overall_avgの算術的正当性を検証
    - **Validates: Requirements 3.3, 11.1, 11.2, 11.3**
  - [x]* 2.5 レベル判定のプロパティテスト（Property 2: レベル判定の正当性）
    - **Property 2: レベル判定の正当性**
    - hypothesisで0.0〜4.0の任意のoverall_avg値を生成し、閾値マッピングとの一致を検証
    - **Validates: Requirements 3.4, 11.4**
  - [x]* 2.6 スコアバリデーションのプロパティテスト（Property 4: スコアバリデーションの正当性）
    - **Property 4: スコアバリデーションの正当性**
    - hypothesisで不正な回答データ（範囲外、非整数、欠損）を生成し、validate_answersがエラーを返すことを検証
    - **Validates: Requirements 3.2, 11.5, 11.6**
  - [x]* 2.7 トラック別項目選択のプロパティテスト（Property 3: トラック別項目選択の正当性）
    - **Property 3: トラック別項目選択の正当性**
    - hypothesisでトラック（business/engineer）を生成し、必要項目が共通6+トラック固有6の12項目であることを検証
    - **Validates: Requirements 2.2, 2.3**

- [x] 3. フィードバック生成モジュール実装
  - [x] 3.1 フィードバック生成モジュールの実装（feedback_generator.py）
    - `backend/lib/feedback_generator.py` を作成
    - `generate_feedback(track, answers, scores)`: bedrock_client.invoke_claudeを使用してフィードバック生成
    - FEEDBACK_SYSTEM_PROMPT: 強み・改善ポイント・次のアクションの3セクションJSON出力を指示
    - Bedrock呼び出し失敗時はNoneを返却（bedrock_client.pyのリトライ機構を活用）
    - strip_code_fenceでLLM出力のコードフェンスを除去してからJSONパース
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_
  - [x]* 3.2 フィードバック構造のプロパティテスト（Property 6: フィードバック構造の正当性）
    - **Property 6: フィードバック構造の正当性**
    - Bedrock呼び出しをモックし、正常なフィードバック結果がstrengths・improvements・next_actionsの3フィールドを含むことを検証
    - **Validates: Requirements 4.2, 4.3**

- [x] 4. Checkpoint - バックエンドコアモジュール確認
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. バックエンドAPIハンドラ実装
  - [x] 5.1 セルフチェック送信ハンドラの実装（selfcheck_handler.py）
    - `backend/handlers/selfcheck_handler.py` を作成
    - POST /selfcheck/submit: リクエストバリデーション → Score_Calculator → Feedback_Generator → DynamoDB保存 → レスポンス返却
    - session_id（UUID v4）、track（business/engineer）、answers（12項目）のバリデーション
    - DynamoDB保存: PK=SESSION#{session_id}, SK=RESULT#selfcheck、全フィールド（user_id=null含む）
    - フィードバック生成失敗時: feedback=null, feedback_unavailable=true で返却
    - 全レスポンスにAccess-Control-Allow-Origin: * ヘッダー付与
    - _Requirements: 3.1, 6.1, 6.2, 6.3, 6.4, 9.3, 10.1, 10.2, 10.3, 10.5, 10.6_
  - [x] 5.2 スキル定義ハンドラの実装（definitions_handler.py）
    - `backend/handlers/definitions_handler.py` を作成
    - GET /selfcheck/definitions: skill_definitions.pyからビジネスユーザー版・エンジニア版のスキル定義データを返却
    - Access-Control-Allow-Origin: * ヘッダー付与
    - _Requirements: 7.1, 7.2, 10.4, 10.6_
  - [x]* 5.3 session_idバリデーションのプロパティテスト（Property 5: session_idバリデーションの正当性）
    - **Property 5: session_idバリデーションの正当性**
    - hypothesisで任意の文字列を生成し、UUID v4形式でない場合にHTTP 400が返ることを検証
    - **Validates: Requirements 9.3, 10.5**
  - [x]* 5.4 APIレスポンス構造のプロパティテスト（Property 8: APIレスポンス構造の正当性）
    - **Property 8: APIレスポンス構造の正当性**
    - hypothesisで有効な回答データを生成し、レスポンスが全必須フィールドを含むことを検証
    - **Validates: Requirements 10.3**
  - [x]* 5.5 CORSヘッダーのプロパティテスト（Property 9: CORSヘッダーの付与）
    - **Property 9: CORSヘッダーの付与**
    - 成功・エラー両方のレスポンスにAccess-Control-Allow-Origin: * が含まれることを検証
    - **Validates: Requirements 10.6**
  - [x]* 5.6 DynamoDB保存レコードのプロパティテスト（Property 7: DynamoDB保存レコードの完全性）
    - **Property 7: DynamoDB保存レコードの完全性**
    - DynamoDB書き込みをモックし、保存レコードがPK/SK形式・全フィールドを含むことを検証
    - **Validates: Requirements 6.1, 6.2, 6.4**

- [x] 6. Checkpoint - バックエンドAPI確認
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. ユニットテスト実装
  - [x] 7.1 スコア集計ユニットテスト（test_score_calculator.py）
    - `tests/unit/test_score_calculator.py` を作成
    - 正常系: 全項目0、全項目4、混合スコアの集計検証
    - 境界値: overall_avg = 0.0, 1.0, 2.0, 3.0, 3.5, 4.0 のレベル判定
    - 異常系: 範囲外スコア、非整数、項目数不足のバリデーションエラー
    - _Requirements: 3.3, 3.4, 11.1〜11.6_
  - [x] 7.2 フィードバック生成ユニットテスト（test_feedback_generator.py）
    - `tests/unit/test_feedback_generator.py` を作成
    - 正常系: Bedrockモック成功時のフィードバック3セクション返却
    - 異常系: Bedrock呼び出し失敗時のNone返却
    - JSONパースエラー時のフォールバック
    - _Requirements: 4.1〜4.5_
  - [x] 7.3 セルフチェックハンドラユニットテスト（test_selfcheck_handler.py）
    - `tests/unit/test_selfcheck_handler.py` を作成
    - 正常系: 有効なリクエストでスコア・レベル・フィードバック返却
    - 異常系: 不正JSON、session_id不正、track不正、answers不正のバリデーション
    - DynamoDB書き込み失敗時のHTTP 500
    - フィードバック生成失敗時のfeedback_unavailable=true
    - _Requirements: 3.1, 3.2, 3.5, 6.3, 9.3, 10.1〜10.6_
  - [x] 7.4 スキル定義ハンドラユニットテスト（test_definitions_handler.py）
    - `tests/unit/test_definitions_handler.py` を作成
    - 正常系: business/engineerの全レベル定義返却
    - CORSヘッダー付与の検証
    - _Requirements: 7.1, 7.2, 10.4, 10.6_

- [x] 8. Checkpoint - バックエンド全テスト確認
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. serverless.yml更新
  - 既存のLv1〜Lv4関連Lambda関数定義を全て削除
  - selfcheckSubmit（POST /selfcheck/submit）とselfcheckDefinitions（GET /selfcheck/definitions）の2関数を追加
  - PASS_THRESHOLD_LV1〜LV4環境変数を削除、aws-marketplace IAM権限を削除
  - 既存リソース定義（DynamoDB両テーブル、GatewayResponse）は全てそのまま保持
  - _Requirements: 10.1, 10.4, 設計書「serverless.yml変更」_

- [x] 10. フロントエンド実装
  - [x] 10.1 API通信層の書き替え（api.js）
    - `frontend/js/api.js` を全面書き替え
    - `submitSelfcheck(sessionId, track, answers)`: POST /selfcheck/submit
    - `getDefinitions()`: GET /selfcheck/definitions
    - 共通fetchラッパー、エラーバナー表示/非表示
    - _Requirements: 3.1, 10.1, 10.4, 12.5_
  - [x] 10.2 セルフチェックアプリロジック（selfcheck-app.js）
    - `frontend/js/selfcheck-app.js` を新規作成
    - Session_Manager: session_id（UUID v4）生成・sessionStorage保存、URLクエリからuser_id取得
    - トラック選択ロジック、セルフチェック回答収集・バリデーション（未回答ハイライト）
    - API送信・結果画面遷移、ローディングインジケーター表示
    - _Requirements: 1.1〜1.4, 3.1, 3.2, 3.5, 5.4, 9.1, 9.2, 9.4, 12.5_
  - [x] 10.3 トップページ（index.html）の書き替え
    - `frontend/index.html` を全面書き替え
    - ヘッダーロゴに双日テックイノベーションのSVGロゴを使用: `https://www.sojitz-ti.com/resources/images/common/logo_stechi.svg`
    - トラック選択UI（ビジネスユーザー / エンジニア）
    - ナビゲーション（セルフチェック、スキル定義、コンピテンシーマップ）
    - 既存デザインテイスト踏襲（#4a7c9b系カラー、Noto Sans JP）
    - _Requirements: 1.1, 1.2, 1.3, 12.2, 12.4_
  - [x] 10.4 セルフチェック画面（selfcheck.html）
    - `frontend/selfcheck.html` を新規作成
    - 共通6項目 + トラック別6項目の表示（合計12項目）
    - 各項目に0-4のRating_Scale（ラベル付き）
    - 送信ボタン、未回答バリデーション、ローディング表示
    - _Requirements: 2.1〜2.5, 3.1, 3.2, 12.3, 12.5_
  - [x] 10.5 結果画面（result.html）
    - `frontend/result.html` を新規作成
    - Skill_Level表示（Lv1〜Lv5 + レベル名称）
    - スコアのバーチャート可視化（共通スコア・トラック別スコア）
    - AIフィードバック表示（強み・改善ポイント・次のアクション）
    - フィードバック未生成時のフォールバックメッセージ
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 12.3_
  - [x] 10.6 スキル定義画面（definitions.html）
    - `frontend/definitions.html` を新規作成
    - ビジネスユーザー版 / エンジニア版のタブ切り替え
    - 選択済みトラックをデフォルト表示
    - Lv1〜Lv5の名称・説明を表示
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 12.3_
  - [x] 10.7 コンピテンシーマップ画面（competency.html）
    - `frontend/competency.html` を新規作成
    - 既存コンピテンシー6要素とAI活用接続ポイントの並列表示
    - 「変化を取り入れ進化させる」をAIセクション主接続点として視覚的に強調
    - _Requirements: 8.1, 8.2, 8.3, 12.3_
  - [x] 10.8 CSSの全面書き替え（style.css）
    - `frontend/css/style.css` を全面書き替え
    - #4a7c9b系カラーパレット、Noto Sans JPフォント
    - レスポンシブデザイン（モバイル幅600px以下対応）
    - 全ページ共通スタイル + 各ページ固有スタイル
    - _Requirements: 12.1, 12.3, 12.4_

- [x] 11. Checkpoint - フロントエンド確認
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. GitHub Actions CI/CDパイプライン更新
  - `.github/workflows/deploy.yml` を更新
  - テスト実行ステップ追加（pytest実行 → デプロイ前にテスト通過を確認）
  - 既存のバックエンド・フロントエンドデプロイステップは維持
  - _Requirements: 設計書「GitHub Actions CI/CDパイプラインも更新」_

- [x] 13. Final checkpoint - 全体確認
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- `backend/lib/bedrock_client.py` は変更不要（既存のリトライ付きBedrock共通クライアントをそのまま流用）
- DynamoDB `ai-levels-results` テーブルを再利用（SK=RESULT#selfcheck で新データ保存）
- DynamoDB `ai-levels-progress` テーブルは定義を残す（削除しない）
- ロゴ: `https://www.sojitz-ti.com/resources/images/common/logo_stechi.svg`（全ページヘッダーで使用）
- Property tests validate universal correctness properties using hypothesis
- Unit tests validate specific examples and edge cases
