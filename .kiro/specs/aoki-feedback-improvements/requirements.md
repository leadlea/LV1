# Requirements Document

## Introduction

青木さん（双日テックイノベーション）からのフィードバックに基づく4つの改善施策を実装する。既存のAIスキルセルフチェックシステム（sojitz-ai-skill-check spec）は全タスク完了済みであり、本specはその運用改善として位置づける。

青木さんの運用案: セルフチェック → 上長と合意 → 半年後に再実施
青木さんの懸念: エンジニアとビジネスユーザーを分ける必要があるのか（インフラSEも多い）

4つの施策:
1. 結果画面に印刷用ビュー追加（上長共有用）
2. 履歴画面に前回比較表示（半年後の再実施で差分を可視化）
3. トラック選択のガイド文言追加（インフラSEの迷いを解消）
4. エンジニア項目の文言調整（コーディング寄り→インフラSEにも適用可能な表現へ）

制約:
- 既存のバックエンドロジック（スコア計算、レベル判定、API構造）は一切変更しない
- 既存のテストを壊さない
- フロントエンド中心の変更で安全に進める

## Glossary

- **Result_Page**: セルフチェック結果画面（result.html）。スコア・レベル・AIフィードバックを表示する
- **Print_View**: CSS `@media print` で制御される印刷用レイアウト。画面表示とは異なるレイアウトで上長共有に適した形式で出力する
- **History_Page**: 履歴画面（history.html）。過去のセルフチェック結果一覧とレベル推移チャートを表示する
- **Comparison_Display**: 履歴テーブルの各行に表示される前回比較情報（スコア増減、レベル変化）
- **Track_Selector**: トップページ（index.html）のトラック選択コンポーネント
- **Guide_Text**: トラック選択画面に表示されるガイダンス文言。インフラSEなど職種に迷うユーザーを支援する
- **Check_Item_Text**: セルフチェック項目のテキスト文言。backend/lib/check_items.py および frontend/js/selfcheck-app.js の ENGINEER_ITEMS に定義される
- **Self_Check_App**: AIスキルセルフチェックWebアプリケーション全体

## Requirements

### Requirement 1: 結果画面の印刷用ビュー

**User Story:** As a 双日テックイノベーション社員, I want to セルフチェック結果を印刷して上長と共有する, so that 上長との合意形成に使える紙面資料を手軽に用意できる

#### Acceptance Criteria

1. WHEN ユーザーがResult_Pageの「印刷」ボタンをクリックした時, THE Self_Check_App SHALL ブラウザの印刷ダイアログを表示する
2. THE Result_Page SHALL 「印刷」ボタンをスコア詳細カードとAIフィードバックカードの下部に配置する
3. WHILE 印刷プレビューまたは印刷出力の状態の場合, THE Print_View SHALL ヘッダーナビゲーション（header要素）を非表示にする
4. WHILE 印刷プレビューまたは印刷出力の状態の場合, THE Print_View SHALL スキルレベルバッジ、スコア詳細（共通スコア・トラック別スコア・総合スコア）、AIフィードバック（強み・改善ポイント・次のアクション）を1ページに収まるレイアウトで表示する
5. WHILE 印刷プレビューまたは印刷出力の状態の場合, THE Print_View SHALL 「印刷」ボタン、「スキル定義を見る」リンク、「もう一度チェック」リンクを非表示にする
6. WHILE 印刷プレビューまたは印刷出力の状態の場合, THE Print_View SHALL 印刷日時を「印刷日: YYYY/MM/DD」の形式でページ下部に表示する
7. THE Print_View SHALL CSS `@media print` メディアクエリのみで実装し、バックエンド変更を伴わない

### Requirement 2: 履歴画面の前回比較表示

**User Story:** As a 双日テックイノベーション社員, I want to 履歴画面で前回のセルフチェック結果との差分を確認する, so that 半年後の再実施時にスキル向上の度合いを把握できる

#### Acceptance Criteria

1. WHEN History_Pageが2件以上の履歴データを表示する時, THE Comparison_Display SHALL 2件目以降の各行に前回比較（共通スコア差分、トラック別スコア差分、総合スコア差分、レベル変化）を表示する
2. WHEN 履歴データが1件のみの場合, THE Comparison_Display SHALL 比較情報を表示せず、差分列にハイフン「-」を表示する
3. WHEN スコアが前回より上昇した場合, THE Comparison_Display SHALL 差分値を緑色（CSS変数 --green）で「+X.XX」の形式で表示する
4. WHEN スコアが前回より下降した場合, THE Comparison_Display SHALL 差分値を赤色（CSS変数 --error）で「-X.XX」の形式で表示する
5. WHEN スコアが前回と同一の場合, THE Comparison_Display SHALL 差分値をグレー色（CSS変数 --text-light）で「±0.00」の形式で表示する
6. WHEN レベルが前回から変化した場合, THE Comparison_Display SHALL レベル変化を「Lv2→Lv3」の形式で表示し、上昇は緑色、下降は赤色で色分けする
7. THE Comparison_Display SHALL フロントエンドJavaScript変更のみで実装し、バックエンドAPI変更を伴わない

### Requirement 3: トラック選択のガイド文言追加

**User Story:** As a インフラSEを含む双日テックイノベーション社員, I want to トラック選択時にどちらを選ぶべきかのガイダンスを確認する, so that 自分の職種に最適なトラックを迷わず選択できる

#### Acceptance Criteria

1. THE Track_Selector SHALL トラック選択カードの上部に「迷ったら」ガイドテキストを表示する。ガイドテキストの内容は「インフラSE・運用担当の方はビジネスユーザートラックも検討ください。エンジニアトラックはコーディング・開発寄りの項目が含まれます。」とする
2. THE Track_Selector SHALL ガイドテキストを視覚的に区別可能なインフォメーションボックス（背景色付き、アイコン付き）として表示する
3. THE Track_Selector SHALL エンジニアトラックカードの説明文に「開発・インフラ・データ分析など」の記載を維持しつつ、「インフラSEの方はビジネスユーザートラックもご検討ください」の補足テキストを追加する
4. THE Track_Selector SHALL HTML変更のみで実装し、バックエンド変更を伴わない

### Requirement 4: エンジニア項目の文言調整

**User Story:** As a インフラSEを含む双日テックイノベーション社員, I want to エンジニアトラックのセルフチェック項目がインフラSEにも当てはまる表現になっている, so that コーディング以外のエンジニアリング業務にも適用できる自己評価ができる

#### Acceptance Criteria

1. THE Check_Item_Text SHALL エンジニア項目 eng_1 のテキストを「AIコーディング支援ツールを日常的に活用している」から「AIによる開発・運用支援ツールを日常的に活用している」に変更する
2. THE Check_Item_Text SHALL エンジニア項目 eng_2 のテキストを「AIを活用したコードレビュー・テスト生成を実践している」から「AIを活用したレビュー・テスト・品質管理を実践している」に変更する
3. THE Check_Item_Text SHALL エンジニア項目 eng_5 のテキストを「AIを活用した開発プロセスの標準化・自動化を推進している」から「AIを活用した開発・運用プロセスの標準化・自動化を推進している」に変更する
4. THE Check_Item_Text SHALL backend/lib/check_items.py の ENGINEER_ITEMS と frontend/js/selfcheck-app.js の ENGINEER_ITEMS のテキストを同一内容に同期する
5. IF テキスト内容をアサートしている既存テストが存在する場合, THEN THE Check_Item_Text SHALL 該当テストのアサーション値を新しいテキストに更新する
6. THE Check_Item_Text SHALL エンジニア項目の項目ID（eng_1〜eng_6）を変更しない
7. THE Check_Item_Text SHALL エンジニア項目のうち eng_3, eng_4, eng_6 のテキストを変更しない（現状のままとする）
