# Requirements Document

## Introduction

双日テックイノベーション向けに、既存の「AI Levels - AIカリキュラム実行システム」を丸ごとリプレイスするWebアプリケーション。既存のコンピテンシー評価制度を壊さず、AIスキルのセルフチェック（自己申告式 0-4スケール）とAIスキル定義（参照表示）を補助レイヤーとして追加する。

3層アーキテクチャ:
- Layer 1: 既存コンピテンシー本体（変更しない・参照のみ）
- Layer 2: AIセルフチェック（全社員共通6項目 + トラック別追加6項目）
- Layer 3: AIスキル定義（ビジネスユーザー版 Lv1-5 / エンジニア版 Lv1-5）

既存のAWSインフラ（Lambda + API Gateway + DynamoDB + Bedrock + S3/CloudFront）を活用し、フロントエンド・バックエンドハンドラ・テストを全面的に書き替える。

## Glossary

- **Self_Check_App**: AIスキルセルフチェックWebアプリケーション全体
- **Check_Form**: セルフチェック回答フォーム画面（0-4スケールの自己申告入力UI）
- **Track_Selector**: ビジネスユーザー / エンジニアのトラック選択コンポーネント
- **Score_Calculator**: セルフチェック回答からスコア集計・レベル判定を行うモジュール
- **Feedback_Generator**: セルフチェック結果に基づきAI（Bedrock Claude）でフィードバックを生成するモジュール
- **Skill_Definition_Viewer**: AIスキル定義（Lv1-5）を参照表示する画面コンポーネント
- **Competency_Map_Viewer**: 既存コンピテンシー6要素とAIスキルの接続を表示するコンポーネント
- **Result_Store**: セルフチェック結果をDynamoDBに保存・取得するバックエンドモジュール
- **Session_Manager**: session_id（UUID v4）ベースの匿名セッション管理モジュール
- **Check_Item**: セルフチェックの個別項目（テキスト + 0-4スケール回答）
- **Track**: ユーザーの職種トラック（business または engineer）
- **Rating_Scale**: 0（未経験）〜 4（周囲に展開できる）の5段階採点スケール
- **Skill_Level**: AIスキル定義のレベル（Lv1〜Lv5）
- **API_Handler**: API Gateway経由でLambdaが処理するバックエンドエンドポイント

## Requirements

### Requirement 1: トラック選択

**User Story:** As a 双日テックイノベーション社員, I want to ビジネスユーザーまたはエンジニアのトラックを選択する, so that 自分の職種に適したセルフチェック項目が表示される

#### Acceptance Criteria

1. WHEN ユーザーがSelf_Check_Appにアクセスした時, THE Track_Selector SHALL 「ビジネスユーザー」と「エンジニア」の2つのトラック選択肢を表示する
2. WHEN ユーザーがトラックを選択した時, THE Track_Selector SHALL 選択されたTrackをSession_Managerに保存し、Check_Form画面へ遷移する
3. WHEN ユーザーがトラックを未選択の状態でCheck_Formへの遷移を試みた時, THE Track_Selector SHALL 遷移を阻止し、トラック選択を促すメッセージを表示する
4. THE Session_Manager SHALL session_id（UUID v4）を自動生成し、sessionStorageに保存する

### Requirement 2: セルフチェック項目表示

**User Story:** As a 双日テックイノベーション社員, I want to 自分のトラックに応じたセルフチェック項目を確認する, so that 適切な項目に対して自己評価できる

#### Acceptance Criteria

1. THE Check_Form SHALL 全社員共通の6項目を全ユーザーに表示する
2. WHILE Trackが「business」の場合, THE Check_Form SHALL 全社員共通6項目に加えてビジネスユーザー追加6項目（合計12項目）を表示する
3. WHILE Trackが「engineer」の場合, THE Check_Form SHALL 全社員共通6項目に加えてエンジニア追加6項目（合計12項目）を表示する
4. THE Check_Form SHALL 各Check_Itemに対して0（未経験）〜4（周囲に展開できる）のRating_Scaleを表示する
5. THE Check_Form SHALL Rating_Scaleの各段階の意味（0: 未経験, 1: 知っている, 2: 使っている, 3: 成果を出している, 4: 周囲に展開できる）をラベルとして表示する

### Requirement 3: セルフチェック回答送信

**User Story:** As a 双日テックイノベーション社員, I want to セルフチェックの回答を送信する, so that 自分のAIスキルレベルが判定される

#### Acceptance Criteria

1. WHEN ユーザーが全Check_Itemに回答して送信ボタンを押した時, THE Check_Form SHALL 回答データ（session_id, track, 各項目のスコア）をAPI_Handlerへ送信する
2. WHEN 未回答のCheck_Itemが存在する状態で送信ボタンが押された時, THE Check_Form SHALL 送信を阻止し、未回答項目をハイライト表示する
3. WHEN API_Handlerが回答データを受信した時, THE Score_Calculator SHALL 全社員共通項目の平均スコアとトラック別追加項目の平均スコアを算出する
4. WHEN API_Handlerが回答データを受信した時, THE Score_Calculator SHALL 平均スコアに基づいてSkill_Level（Lv1〜Lv5）を判定する
5. IF API_Handlerへの送信が失敗した場合, THEN THE Check_Form SHALL エラーメッセージとリトライボタンを表示する

### Requirement 4: AIフィードバック生成

**User Story:** As a 双日テックイノベーション社員, I want to セルフチェック結果に基づくAIからのフィードバックを受け取る, so that 自分のAIスキル向上の具体的なアクションがわかる

#### Acceptance Criteria

1. WHEN Score_Calculatorがスコア集計とレベル判定を完了した時, THE Feedback_Generator SHALL セルフチェック結果（track, 各項目スコア, 判定レベル）をBedrock Claudeに送信してフィードバックを生成する
2. THE Feedback_Generator SHALL フィードバックとして「強み」「改善ポイント」「具体的な次のアクション」の3セクションを含むテキストを生成する
3. THE Feedback_Generator SHALL フィードバックをJSON形式（strengths, improvements, next_actions の3フィールド）で返却する
4. IF Bedrock Claudeの呼び出しが失敗した場合, THEN THE Feedback_Generator SHALL 最大3回のリトライ（指数バックオフ）を実行する
5. IF リトライ上限を超えてもフィードバック生成が失敗した場合, THEN THE Feedback_Generator SHALL スコアとレベル判定のみを返却し、フィードバック未生成の旨を示すフラグを含める

### Requirement 5: 結果表示

**User Story:** As a 双日テックイノベーション社員, I want to セルフチェックの結果を視覚的に確認する, so that 自分のAIスキルの現状を把握できる

#### Acceptance Criteria

1. WHEN API_Handlerが結果を返却した時, THE Self_Check_App SHALL 判定されたSkill_Level（Lv1〜Lv5）をレベル名称とともに表示する
2. WHEN API_Handlerが結果を返却した時, THE Self_Check_App SHALL 全社員共通スコアとトラック別スコアをレーダーチャートまたはバーチャートで可視化する
3. WHEN API_Handlerが結果を返却した時, THE Self_Check_App SHALL AIフィードバック（強み・改善ポイント・次のアクション）を表示する
4. WHEN フィードバック未生成フラグが含まれる場合, THE Self_Check_App SHALL スコアとレベル判定のみを表示し、「フィードバックは現在取得できません」のメッセージを表示する

### Requirement 6: 結果のDynamoDB保存

**User Story:** As a システム管理者, I want to セルフチェック結果をDynamoDBに永続化する, so that 将来的なuser_id紐付けや集計分析に活用できる

#### Acceptance Criteria

1. WHEN Score_Calculatorがスコア集計を完了した時, THE Result_Store SHALL 結果レコード（session_id, track, 各項目スコア, 平均スコア, 判定レベル, フィードバック, completed_at）をDynamoDB resultsテーブルに保存する
2. THE Result_Store SHALL DynamoDBのPKを「SESSION#{session_id}」、SKを「RESULT#selfcheck」の形式で保存する
3. IF DynamoDBへの書き込みが失敗した場合, THEN THE Result_Store SHALL エラーログを出力し、HTTPステータス500とリトライ可能なエラーメッセージを返却する
4. THE Result_Store SHALL 将来的なuser_id紐付けに備え、user_idフィールドをオプショナルとしてスキーマに含める

### Requirement 7: AIスキル定義表示

**User Story:** As a 双日テックイノベーション社員, I want to AIスキル定義（Lv1〜Lv5）の詳細を参照する, so that 各レベルに求められるスキルを理解できる

#### Acceptance Criteria

1. THE Skill_Definition_Viewer SHALL ビジネスユーザー版のスキル定義（Lv1: 安全利用の基本者, Lv2: 効率化実践者, Lv3: 能力増幅実践者, Lv4: 他者貢献・再利用化, Lv5: 変革リーダー）を表示する
2. THE Skill_Definition_Viewer SHALL エンジニア版のスキル定義（Lv1: エントリー, Lv2: 基礎の自走, Lv3: 自立実装, Lv4: 社内リード, Lv5: 社内ハイエンド）を表示する
3. WHEN ユーザーがトラックを選択済みの場合, THE Skill_Definition_Viewer SHALL 選択済みトラックのスキル定義をデフォルトで表示する
4. THE Skill_Definition_Viewer SHALL ビジネスユーザー版とエンジニア版をタブまたはトグルで切り替え可能にする

### Requirement 8: 既存コンピテンシー接続表示

**User Story:** As a 双日テックイノベーション社員, I want to 既存コンピテンシー6要素とAIスキルの関連を確認する, so that 既存の評価制度との接続を理解できる

#### Acceptance Criteria

1. THE Competency_Map_Viewer SHALL 既存コンピテンシー6要素（お客さまの変化と本質を読み解く, お客様の期待を超える提案をする, 行動につなげる計画と遂行のマネジメント, 変化を取り入れ進化させる, 意図を伝えるコミュニケーション, チームを導くリーダーシップ）を表示する
2. THE Competency_Map_Viewer SHALL 各コンピテンシー要素に対応するAI活用の接続ポイント（情報収集・要約・論点整理, 提案品質の増幅, 計画・分解・実行支援, AIセクションの主接続点, 伝達品質の向上, 周囲展開・標準化）を並列表示する
3. THE Competency_Map_Viewer SHALL 「変化を取り入れ進化させる」をAIセクションの主接続点として視覚的に強調表示する

### Requirement 9: セッション管理

**User Story:** As a ユーザー, I want to ログインなしでセルフチェックを実行する, so that 手軽にAIスキルの自己評価ができる

#### Acceptance Criteria

1. THE Session_Manager SHALL ページアクセス時にsession_id（UUID v4）を自動生成し、sessionStorageに保存する
2. THE Session_Manager SHALL 全APIリクエストにsession_idを付与する
3. WHEN session_idが不正な形式（UUID v4以外）の場合, THE API_Handler SHALL HTTPステータス400とエラーメッセージを返却する
4. THE Session_Manager SHALL 将来的なuser_id紐付けに備え、URLクエリパラメーターからuser_idを取得する機能を実装する（オプショナル）

### Requirement 10: バックエンドAPI設計

**User Story:** As a 開発者, I want to セルフチェックのバックエンドAPIが明確に定義されている, so that フロントエンドとバックエンドを独立して開発できる

#### Acceptance Criteria

1. THE API_Handler SHALL POST /selfcheck/submit エンドポイントで回答データを受け付け、スコア集計・レベル判定・フィードバック生成・結果保存を実行する
2. THE API_Handler SHALL POST /selfcheck/submit のリクエストボディとして session_id（string, UUID v4）, track（string, "business" | "engineer"）, answers（object, 各項目IDをキー・0-4の整数を値とするマップ）を受け付ける
3. THE API_Handler SHALL POST /selfcheck/submit のレスポンスとして session_id, track, common_avg（number）, track_avg（number）, overall_avg（number）, skill_level（string, "Lv1"〜"Lv5"）, feedback（object | null）を返却する
4. THE API_Handler SHALL GET /selfcheck/definitions エンドポイントでスキル定義データ（ビジネスユーザー版・エンジニア版）を返却する
5. IF リクエストボディのバリデーションに失敗した場合, THEN THE API_Handler SHALL HTTPステータス400と具体的なエラーメッセージを返却する
6. THE API_Handler SHALL 全レスポンスにAccess-Control-Allow-Origin: * ヘッダーを付与する

### Requirement 11: スコア集計・レベル判定ロジック

**User Story:** As a 開発者, I want to スコア集計とレベル判定のロジックが明確に定義されている, so that 一貫した判定結果を提供できる

#### Acceptance Criteria

1. THE Score_Calculator SHALL 全社員共通6項目のスコア平均値（common_avg）を算出する
2. THE Score_Calculator SHALL トラック別追加6項目のスコア平均値（track_avg）を算出する
3. THE Score_Calculator SHALL common_avgとtrack_avgの加重平均（overall_avg）を算出する（重みは均等: 50:50）
4. THE Score_Calculator SHALL overall_avgに基づいて以下のSkill_Levelを判定する: 0.0以上1.0未満→Lv1, 1.0以上2.0未満→Lv2, 2.0以上3.0未満→Lv3, 3.0以上3.5未満→Lv4, 3.5以上4.0以下→Lv5
5. THE Score_Calculator SHALL 各項目のスコアが0〜4の整数であることをバリデーションする
6. IF スコアが0〜4の範囲外の場合, THEN THE Score_Calculator SHALL バリデーションエラーを返却する

### Requirement 12: フロントエンドUI設計

**User Story:** As a 双日テックイノベーション社員, I want to 洗練されたUIでセルフチェックを実行する, so that 快適にAIスキルの自己評価ができる

#### Acceptance Criteria

1. THE Self_Check_App SHALL HTML / CSS / Vanilla JSで実装し、S3 + CloudFrontで静的ホスティングする
2. THE Self_Check_App SHALL トップページ（トラック選択）、セルフチェック画面、結果画面、スキル定義画面、コンピテンシーマップ画面のページ構成とする
3. THE Self_Check_App SHALL レスポンシブデザインでモバイル端末（幅600px以下）にも対応する
4. THE Self_Check_App SHALL 既存の提案資料のデザインテイスト（洗練されたUI、Noto Sans JPフォント、#4a7c9b系のカラーパレット）を踏襲する
5. WHILE API通信中の場合, THE Self_Check_App SHALL ローディングインジケーターを表示する

