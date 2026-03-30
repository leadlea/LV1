# Implementation Plan: 青木フィードバック改善

## 概要

青木さんからの運用フィードバックに基づく4つの改善施策を、フロントエンド中心の安全な変更で実装する。既存のバックエンドロジック（スコア計算、レベル判定、API構造）は一切変更しない。施策ごとに独立して進め、各施策完了後にチェックポイントを設ける。

## Tasks

- [x] 1. 施策4: エンジニア項目の文言調整（バックエンド + フロントエンド）
  - [x] 1.1 `backend/lib/check_items.py` の ENGINEER_ITEMS テキスト変更
    - eng_1: 「AIコーディング支援ツールを日常的に活用している」→「AIによる開発・運用支援ツールを日常的に活用している」
    - eng_2: 「AIを活用したコードレビュー・テスト生成を実践している」→「AIを活用したレビュー・テスト・品質管理を実践している」
    - eng_5: 「AIを活用した開発プロセスの標準化・自動化を推進している」→「AIを活用した開発・運用プロセスの標準化・自動化を推進している」
    - eng_3, eng_4, eng_6 は変更しない。項目ID（eng_1〜eng_6）は不変
    - _Requirements: 4.1, 4.2, 4.3, 4.6, 4.7_

  - [x] 1.2 `frontend/js/selfcheck-app.js` の ENGINEER_ITEMS テキスト変更
    - eng_1, eng_2, eng_5 を `check_items.py` と同一テキストに更新
    - eng_3, eng_4, eng_6 は変更しない
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.6, 4.7_

  - [x]* 1.3 Property 4 のプロパティテスト作成（`tests/property/test_item_sync_properties.py`）
    - **Property 4: エンジニア項目テキストのバックエンド/フロントエンド同期**
    - `backend/lib/check_items.py` の ENGINEER_ITEMS と `frontend/js/selfcheck-app.js` の ENGINEER_ITEMS のテキストが全項目で一致することを検証
    - hypothesis を使用し、任意のエンジニア項目IDに対してバックエンド/フロントエンド間のテキスト同一性を検証
    - **Validates: Requirements 4.4**

  - [x]* 1.4 エンジニア項目テキスト変更のユニットテスト作成（`tests/unit/test_check_items_text.py`）
    - eng_1, eng_2, eng_5 が新テキストに更新されていることを検証
    - eng_3, eng_4, eng_6 が変更されていないことを検証
    - 項目ID（eng_1〜eng_6）が全て保持されていることを検証
    - 既存テスト（test_score_properties.py, test_feedback_properties.py）がテキスト内容をアサートしていないことを確認済み
    - _Requirements: 4.1, 4.2, 4.3, 4.5, 4.6, 4.7_

- [x] 2. チェックポイント - 施策4完了確認
  - 既存テスト（pytest）が全てパスすることを確認する。`pytest tests/ -v` を実行
  - 新規テスト（test_item_sync_properties.py, test_check_items_text.py）がパスすることを確認
  - ユーザーに質問があれば確認する

- [x] 3. 施策1: 結果画面の印刷用ビュー追加
  - [x] 3.1 `frontend/css/style.css` に `@media print` セクション追加
    - `header`（ナビゲーション）: `display: none`
    - `.print-btn`, ボタンリンク群: `display: none`
    - `.step-indicator`: `display: none`
    - `.result-hero`, `.card`, `.feedback-section`: 印刷最適化（余白縮小、影削除、ボーダー簡素化）
    - `.print-date`: `display: block`（画面表示時は `display: none`）
    - `body`: 背景白、フォントサイズ調整
    - `@page`: マージン設定で1ページに収まるよう調整
    - _Requirements: 1.3, 1.4, 1.5, 1.6, 1.7_

  - [x] 3.2 `frontend/result.html` に印刷ボタンと印刷日時要素を追加
    - 印刷ボタン（`🖨️ 印刷`）をスコア詳細カードとAIフィードバックカードの下部、既存ボタン群の横に配置
    - `onclick="window.print()"` でブラウザ印刷ダイアログを呼び出す
    - 印刷日時用の非表示要素（`.print-date`）を追加し、JSで `YYYY/MM/DD` 形式の日付を設定
    - _Requirements: 1.1, 1.2, 1.6_

- [x] 4. 施策3: トラック選択のガイド文言追加
  - [x] 4.1 `frontend/index.html` にガイドボックスHTML追加
    - `.track-grid` の直前に `guide-box` を配置
    - ガイドテキスト: 「迷ったら：インフラSE・運用担当の方はビジネスユーザートラックも検討ください。エンジニアトラックはコーディング・開発寄りの項目が含まれます。」
    - 💡アイコン付き、背景色（`--accent-light`）で視覚的に区別
    - _Requirements: 3.1, 3.2, 3.4_

  - [x] 4.2 `frontend/index.html` のエンジニアカードに補足テキスト追加
    - エンジニアトラックカードの説明文の下に「※インフラSEの方はビジネスユーザートラックもご検討ください」を追加
    - 既存の「開発・インフラ・データ分析など」の記載は維持
    - _Requirements: 3.3, 3.4_

  - [x] 4.3 `frontend/css/style.css` に `.guide-box` スタイル追加
    - flexbox レイアウト、`--accent-light` 背景、角丸、適切な余白
    - _Requirements: 3.2_

- [x] 5. チェックポイント - 施策1・3完了確認
  - 既存テストが全てパスすることを確認する
  - ユーザーに質問があれば確認する

- [x] 6. 施策2: 履歴画面の前回比較表示
  - [x] 6.1 `frontend/history.html` のテーブルヘッダーに「前回比較」列を追加
    - 既存: `日時 | トラック | 共通 | トラック別 | 総合 | レベル`
    - 変更後: `日時 | トラック | 共通 | トラック別 | 総合 | レベル | 前回比較`
    - _Requirements: 2.1_

  - [x] 6.2 `frontend/history.html` の `renderTable` 関数に前回比較ロジックを実装
    - 2件目以降の各行に前回比較（共通スコア差分、トラック別スコア差分、総合スコア差分、レベル変化）を表示
    - 初回（i=0）は比較なし → 「-」表示
    - 差分フォーマット: 上昇=`+X.XX`（緑 `--green`）、下降=`-X.XX`（赤 `--error`）、同一=`±0.00`（グレー `--text-light`）
    - レベル変化: `LvX→LvY`（上昇=緑、下降=赤）、同一の場合は変化なし表示
    - 防御的に `isNaN` チェックを入れ、NaN時は「-」表示
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [x]* 6.3 Property 1, 2, 3 のプロパティテスト作成（`tests/property/test_comparison_properties.py`）
    - **Property 1: 前回比較の差分計算正当性**
    - 任意の2件以上の履歴結果リストに対して、i番目（i≥1）の差分が `results[i].score - results[i-1].score` と一致し、初回（i=0）の差分は計算されないことを検証
    - **Validates: Requirements 2.1**
    - **Property 2: 差分フォーマットの符号・値正当性**
    - 任意の2つのスコア値（0.00〜4.00）に対して、差分>0→`+X.XX`/緑、差分<0→`-X.XX`/赤、差分=0→`±0.00`/グレーを検証
    - **Validates: Requirements 2.3, 2.4, 2.5**
    - **Property 3: レベル変化フォーマットの正当性**
    - 任意の2つのスキルレベル（Lv1〜Lv5）に対して、レベル変化時は `LvX→LvY` 形式、上昇=緑、下降=赤を検証
    - **Validates: Requirements 2.6**
    - フロントエンドJSの比較ロジックをPythonで再実装してhypothesisでテスト

- [x] 7. 最終チェックポイント - 全施策完了確認
  - `pytest tests/ -v` で全テスト（既存 + 新規）がパスすることを確認する
  - ユーザーに質問があれば確認する

## Notes

- `*` 付きタスクはオプションであり、MVP優先時はスキップ可能
- 各タスクは要件への参照を含み、トレーサビリティを確保
- チェックポイントでインクリメンタルに検証
- プロパティテストは hypothesis（Python）で実装（既存プロジェクトと同一）
- 施策4を最初に実施する理由: バックエンド/フロントエンド両方の変更を含むため、早期に同期を確認する
