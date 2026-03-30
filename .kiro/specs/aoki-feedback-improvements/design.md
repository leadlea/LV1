# デザインドキュメント: 青木フィードバック改善

## 概要

既存のAIスキルセルフチェックシステム（sojitz-ai-skill-check spec 完了済み）に対し、青木さんからの運用フィードバックに基づく4つの改善施策を実装する。

青木さんの運用案: セルフチェック → 上長と合意 → 半年後に再実施
青木さんの懸念: エンジニアとビジネスユーザーを分ける必要があるのか（インフラSEも多い）

### 施策一覧

| # | 施策 | 変更対象 | 影響範囲 |
|---|------|---------|---------|
| 1 | 結果画面に印刷用ビュー追加 | `frontend/css/style.css`（`@media print`追加）、`frontend/result.html`（印刷ボタン追加） | CSS・HTML のみ |
| 2 | 履歴画面に前回比較表示 | `frontend/history.html`（JS変更） | フロントエンドJSのみ |
| 3 | トラック選択のガイド文言追加 | `frontend/index.html`（HTML追加） | HTMLのみ |
| 4 | エンジニア項目の文言調整 | `backend/lib/check_items.py`、`frontend/js/selfcheck-app.js` | 項目テキスト3箇所変更 |

### 変更しないもの

- `backend/lib/score_calculator.py`（スコア計算・レベル判定ロジック）
- `backend/lib/bedrock_client.py`（Bedrock共通クライアント）
- `backend/lib/feedback_generator.py`（フィードバック生成）
- `backend/handlers/selfcheck_handler.py`（APIハンドラ）
- `backend/handlers/history_handler.py`（履歴APIハンドラ）
- `serverless.yml`（インフラ定義）
- DynamoDBスキーマ・API構造

## アーキテクチャ

本改善は既存アーキテクチャに変更を加えない。全施策はフロントエンド層（HTML/CSS/JS）と項目テキスト定義の変更のみで完結する。

```mermaid
graph TB
    subgraph "変更対象（フロントエンド）"
        R[result.html<br/>印刷ボタン追加]
        CSS[style.css<br/>@media print 追加]
        H[history.html<br/>前回比較JS追加]
        I[index.html<br/>ガイド文言HTML追加]
        JS[selfcheck-app.js<br/>eng項目テキスト変更]
    end

    subgraph "変更対象（バックエンド項目定義のみ）"
        CI[check_items.py<br/>eng項目テキスト変更]
    end

    subgraph "変更なし"
        SC[score_calculator.py]
        FG[feedback_generator.py]
        SH[selfcheck_handler.py]
        HH[history_handler.py]
        BC[bedrock_client.py]
        DB[(DynamoDB)]
    end

    R --> CSS
    CI -.->|テキスト同期| JS
```

## コンポーネントとインターフェース

### 施策1: 印刷用ビュー（result.html + style.css）

**変更ファイル:**
- `frontend/result.html`: 印刷ボタン追加、印刷日時用の非表示要素追加
- `frontend/css/style.css`: `@media print` セクション追加

**印刷ボタン:**
```html
<button id="print-btn" class="btn btn-secondary print-btn" type="button" onclick="window.print()">🖨️ 印刷</button>
```

配置場所: スコア詳細カードとAIフィードバックカードの下部、既存の「スキル定義を見る」「もう一度チェック」ボタンの横。

**印刷日時要素:**
```html
<div class="print-date" id="print-date"></div>
```
画面表示時は `display: none`、印刷時のみ表示。JSで `YYYY/MM/DD` 形式の日付を設定。

**CSS @media print ルール:**
- `header`（ナビゲーション）: `display: none`
- `.print-btn`, `.btn-secondary`（印刷ボタン・リンクボタン）: `display: none`
- `.step-indicator`（ステップインジケーター）: `display: none`
- `.result-hero`, `.card`, `.feedback-section`: 印刷最適化（余白縮小、影削除、ボーダー簡素化）
- `.print-date`: `display: block`、ページ下部に表示
- `body`: 背景白、フォントサイズ調整
- `@page`: マージン設定で1ページに収まるよう調整

### 施策2: 前回比較表示（history.html）

**変更ファイル:** `frontend/history.html`（インラインJS変更のみ）

**テーブルヘッダー変更:**
既存: `日時 | トラック | 共通 | トラック別 | 総合 | レベル`
変更後: `日時 | トラック | 共通 | トラック別 | 総合 | レベル | 前回比較`

**比較ロジック（フロントエンドJS）:**
```javascript
function renderTable(results) {
  // results は oldest-first（API ScanIndexForward=true）
  results.forEach((r, i) => {
    if (i === 0) {
      // 初回: 比較なし → "-"
    } else {
      const prev = results[i - 1];
      const commonDiff = parseFloat(r.common_avg) - parseFloat(prev.common_avg);
      const trackDiff = parseFloat(r.track_avg) - parseFloat(prev.track_avg);
      const overallDiff = parseFloat(r.overall_avg) - parseFloat(prev.overall_avg);
      const levelChanged = r.skill_level !== prev.skill_level;
      // 差分表示: +X.XX（緑）、-X.XX（赤）、±0.00（グレー）
    }
  });
}
```

**差分表示フォーマット:**
- 上昇: `<span style="color:var(--green)">+0.50</span>`
- 下降: `<span style="color:var(--error)">-0.33</span>`
- 同一: `<span style="color:var(--text-light)">±0.00</span>`
- レベル変化: `Lv2→Lv3`（上昇=緑、下降=赤）

### 施策3: トラック選択ガイド文言（index.html）

**変更ファイル:** `frontend/index.html`（HTML追加のみ）

**ガイドテキスト:**
トラック選択カード（`.track-grid`）の直前に配置。

```html
<div class="guide-box">
  <span class="guide-icon">💡</span>
  <div class="guide-text">
    <strong>迷ったら</strong>：インフラSE・運用担当の方はビジネスユーザートラックも検討ください。
    エンジニアトラックはコーディング・開発寄りの項目が含まれます。
  </div>
</div>
```

**エンジニアカード補足:**
既存の `<p>開発・インフラ・データ分析など<br>AI技術を実装に活用する方</p>` の下に補足テキスト追加:
```html
<p style="font-size:11px;color:var(--text-light);margin-top:6px;">
  ※インフラSEの方はビジネスユーザートラックもご検討ください
</p>
```

**ガイドボックスCSS:**
```css
.guide-box {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 14px 16px;
  background: var(--accent-light);
  border-radius: var(--radius-sm);
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--text-mid);
  line-height: 1.7;
}
```

### 施策4: エンジニア項目テキスト変更

**変更ファイル:**
- `backend/lib/check_items.py`: ENGINEER_ITEMS の eng_1, eng_2, eng_5 テキスト変更
- `frontend/js/selfcheck-app.js`: ENGINEER_ITEMS の eng_1, eng_2, eng_5 テキスト変更

**変更内容:**

| 項目ID | 変更前 | 変更後 |
|--------|--------|--------|
| eng_1 | AIコーディング支援ツールを日常的に活用している | AIによる開発・運用支援ツールを日常的に活用している |
| eng_2 | AIを活用したコードレビュー・テスト生成を実践している | AIを活用したレビュー・テスト・品質管理を実践している |
| eng_5 | AIを活用した開発プロセスの標準化・自動化を推進している | AIを活用した開発・運用プロセスの標準化・自動化を推進している |

**変更しない項目:** eng_3, eng_4, eng_6（現状維持）
**変更しないフィールド:** 全項目のID（eng_1〜eng_6）は不変

**テスト影響:**
既存テストでエンジニア項目テキストをアサートしているものがあれば、新テキストに更新する必要がある。ただし、既存のプロパティテスト（`test_score_properties.py`, `test_feedback_properties.py`）は項目IDのみを使用しており、テキスト内容をアサートしていないため影響なし。

## データモデル

本改善ではデータモデルに変更なし。

- DynamoDBスキーマ: 変更なし
- APIリクエスト/レスポンス構造: 変更なし
- sessionStorage構造: 変更なし
- 履歴API（`GET /selfcheck/history`）のレスポンス: 変更なし（フロントエンドで既存データから差分を計算）

既存の履歴APIレスポンス構造（変更なし）:
```json
{
  "user_id": "STI-001",
  "results": [
    {
      "completed_at": "2024-01-15T10:00:00+00:00",
      "track": "business",
      "common_avg": "2.50",
      "track_avg": "2.00",
      "overall_avg": "2.25",
      "skill_level": "Lv3",
      "feedback": { "strengths": "...", "improvements": "...", "next_actions": "..." }
    }
  ]
}
```

前回比較はフロントエンドJSで `results[i]` と `results[i-1]` の差分を計算するのみ。


## 正当性プロパティ

*プロパティとは、システムの全ての有効な実行において成り立つべき特性や振る舞いのことである。人間が読める仕様と機械的に検証可能な正当性保証の橋渡しとなる形式的な記述である。*

### Prework分析からの導出

本改善は主にフロントエンド（HTML/CSS/JS）の変更であり、CSS `@media print` やHTML構造変更はプロパティベーステストの対象外。テスト可能なプロパティは以下の4つに集約される。

- 施策1（印刷ビュー）: CSS/HTMLのみのため、プロパティベーステスト対象外。手動テストで検証。
- 施策2（前回比較）: 差分計算・フォーマットロジックがプロパティテスト可能。
- 施策3（ガイド文言）: HTML追加のみのため、プロパティベーステスト対象外。
- 施策4（文言調整）: バックエンド/フロントエンド間のテキスト同期がプロパティテスト可能。

### Property 1: 前回比較の差分計算正当性

*任意の*2件以上の履歴結果リスト（各結果は common_avg, track_avg, overall_avg を持つ数値）に対して、i番目（i≥1）の結果の差分は `results[i].score - results[i-1].score` と一致し、初回（i=0）の差分は計算されないこと。

**Validates: Requirements 2.1**

### Property 2: 差分フォーマットの符号・値正当性

*任意の*2つの連続するスコア値（0.00〜4.00の範囲）に対して、差分フォーマット関数は以下を満たすこと:
- 差分 > 0 の場合: `+X.XX` 形式の文字列を返し、色指定は緑（`--green`）
- 差分 < 0 の場合: `-X.XX` 形式の文字列を返し、色指定は赤（`--error`）
- 差分 = 0 の場合: `±0.00` 形式の文字列を返し、色指定はグレー（`--text-light`）

**Validates: Requirements 2.3, 2.4, 2.5**

### Property 3: レベル変化フォーマットの正当性

*任意の*2つの連続するスキルレベル（Lv1〜Lv5）に対して、レベル変化フォーマット関数は以下を満たすこと:
- レベルが異なる場合: `LvX→LvY` 形式の文字列を返す
- レベル数値が上昇した場合: 色指定は緑
- レベル数値が下降した場合: 色指定は赤
- レベルが同一の場合: 変化なしを示す表示を返す

**Validates: Requirements 2.6**

### Property 4: エンジニア項目テキストのバックエンド/フロントエンド同期

*任意の*エンジニア項目（eng_1〜eng_6）に対して、`backend/lib/check_items.py` の ENGINEER_ITEMS に定義されたテキストと `frontend/js/selfcheck-app.js` の ENGINEER_ITEMS に定義されたテキストは同一であること。

**Validates: Requirements 4.4**

## エラーハンドリング

本改善ではエラーハンドリングの変更は最小限。

### 施策1: 印刷用ビュー
- `window.print()` はブラウザネイティブAPIであり、エラーハンドリング不要
- 印刷日時の生成は `new Date()` のみで外部依存なし

### 施策2: 前回比較表示
- 履歴データが0件の場合: 既存の「履歴はまだありません」表示がそのまま機能
- 履歴データが1件の場合: 比較列に「-」を表示（エラーではなく正常動作）
- スコア値が数値でない場合: `parseFloat()` で `NaN` になる可能性があるが、APIレスポンスは常に数値文字列を返すため実運用上は発生しない。防御的に `isNaN` チェックを入れ、NaN時は「-」表示とする

### 施策3: ガイド文言
- 静的HTML追加のみ。エラーハンドリング不要

### 施策4: エンジニア項目テキスト変更
- テキスト変更のみ。項目IDは不変のため、既存のスコア計算・バリデーションロジックに影響なし
- 既存テストでテキスト内容をアサートしているものがあれば更新が必要（調査済み: 既存プロパティテストはIDのみ使用、テキストアサートなし）

## テスト戦略

### テストフレームワーク

- **バックエンド**: pytest + hypothesis（既存と同一）
- **フロントエンド**: 手動テスト + プロパティテスト用にJS比較ロジックをPythonで再実装してテスト

### プロパティベーステスト

プロパティベーステストライブラリとして **hypothesis**（Python）を使用する（既存プロジェクトと同一）。

各プロパティテストは最低100回のイテレーションで実行する。各テストにはデザインドキュメントのプロパティ番号を参照するコメントタグを付与する。

タグ形式: **Feature: aoki-feedback-improvements, Property {number}: {property_text}**

各正当性プロパティは1つのプロパティベーステストで実装する。

### テスト構成

```
tests/
├── unit/
│   ├── test_check_items_text.py          # 施策4: エンジニア項目テキスト変更の検証
│   └── (既存テストは変更なし)
└── property/
    ├── test_comparison_properties.py      # Property 1, 2, 3: 前回比較ロジック
    ├── test_item_sync_properties.py       # Property 4: テキスト同期
    └── (既存テストは変更なし)
```

### ユニットテスト

ユニットテストはプロパティベーステストを補完し、以下に焦点を当てる:
- エンジニア項目 eng_1, eng_2, eng_5 のテキストが新しい文言に更新されていること
- エンジニア項目 eng_3, eng_4, eng_6 のテキストが変更されていないこと
- 項目ID（eng_1〜eng_6）が全て保持されていること
- 履歴1件のみの場合の比較表示（エッジケース）
- スコア差分が0の場合の「±0.00」表示（エッジケース）

### 手動テスト項目

以下はプロパティベーステストでカバーできないため、手動テストで検証する:
- 印刷プレビューでヘッダーが非表示になること
- 印刷プレビューでボタン類が非表示になること
- 印刷プレビューで1ページに収まること
- 印刷日時が正しい形式で表示されること
- ガイドボックスが視覚的に区別可能であること
- エンジニアカードに補足テキストが表示されること

### 既存テストへの影響

- `tests/property/test_score_properties.py`: 影響なし（項目IDのみ使用）
- `tests/property/test_feedback_properties.py`: 影響なし（項目IDのみ使用）
- `tests/unit/test_selfcheck_handler.py`: 影響なし（テキスト内容をアサートしていない）
- `tests/unit/test_score_calculator.py`: 影響なし（テキスト内容をアサートしていない）
