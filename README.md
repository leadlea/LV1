# AI Levels - AIカリキュラム実行システム

🔗 **https://d2iarskyjm3rk1.cloudfront.net/**

3つのAIエージェント（出題・採点・レビュー）が連動し、カリキュラム「分業設計×依頼設計×品質担保×2ケース再現」をブラウザ上でログインなしに実行できるシステム。

## システムアーキテクチャ

```mermaid
graph TB
    subgraph "フロントエンド"
        Browser[ユーザーブラウザ]
        CF[CloudFront<br/>E1SGV7O9QH5NRD]
        S3[S3 バケット<br/>ai-levels]
    end

    subgraph "バックエンド API"
        APIGW[API Gateway REST]
        subgraph "Lambda - Python 3.12"
            Gen1[出題 Lambda<br/>POST /lv1/generate]
            Grade1[採点+レビュー Lambda<br/>POST /lv1/grade]
            Complete1[完了保存 Lambda<br/>POST /lv1/complete]
            Gen2[出題 Lambda<br/>POST /lv2/generate]
            Grade2[採点+レビュー Lambda<br/>POST /lv2/grade]
            Complete2[完了保存 Lambda<br/>POST /lv2/complete]
            Gen3[出題 Lambda<br/>POST /lv3/generate]
            Grade3[採点+レビュー Lambda<br/>POST /lv3/grade]
            Complete3[完了保存 Lambda<br/>POST /lv3/complete]
            Gen4[出題 Lambda<br/>POST /lv4/generate]
            Grade4[採点+レビュー Lambda<br/>POST /lv4/grade]
            Complete4[完了保存 Lambda<br/>POST /lv4/complete]
            Gate[ゲーティング Lambda<br/>GET /levels/status]
        end
    end

    subgraph "AWSサービス"
        Bedrock[Amazon Bedrock<br/>Claude Sonnet 4.6]
        DDB_R[DynamoDB<br/>ai-levels-results]
        DDB_P[DynamoDB<br/>ai-levels-progress]
    end

    Browser --> CF --> S3
    Browser -->|REST API| APIGW
    APIGW --> Gen1 & Gen2 & Gen3 & Gen4
    APIGW --> Grade1 & Grade2 & Grade3 & Grade4
    APIGW --> Complete1 & Complete2 & Complete3 & Complete4
    APIGW --> Gate
    Gen1 & Gen2 & Gen3 & Gen4 --> Bedrock
    Grade1 & Grade2 & Grade3 & Grade4 --> Bedrock
    Complete1 & Complete2 & Complete3 & Complete4 --> DDB_R
    Complete1 & Complete2 & Complete3 & Complete4 --> DDB_P
    Gate --> DDB_P
```

## 3エージェント連動パイプライン

```mermaid
sequenceDiagram
    participant U as ユーザー
    participant FE as フロントエンド
    participant API as API Gateway
    participant TG as 出題エージェント
    participant G as 採点エージェント
    participant TR as ThresholdResolver
    participant R as レビューエージェント
    participant BR as Bedrock Claude Sonnet 4.6
    participant DB as DynamoDB

    U->>FE: テスト開始
    FE->>API: POST /lvN/generate
    API->>TG: 出題リクエスト
    TG->>BR: プロンプト送信
    BR-->>TG: 3問のテスト生成
    TG-->>FE: questions JSON

    loop 各設問 (step 1〜3)
        U->>FE: 回答入力・送信
        FE->>API: POST /lvN/grade
        API->>G: 採点リクエスト
        G->>BR: 採点プロンプト
        BR-->>G: passed + score
        G->>TR: resolve_passed(level, score)
        TR-->>G: passed (閾値ベース)
        G->>R: レビュー依頼
        R->>BR: フィードバック生成
        BR-->>R: feedback + explanation
        R-->>G: レビュー結果
        G-->>FE: 採点+レビュー結果
        FE->>U: スコア・フィードバック表示
    end

    FE->>API: POST /lvN/complete
    API->>DB: 結果保存 (results)
    API->>DB: 進捗更新 (progress)
    DB-->>FE: saved: true
```

## ゲーティング構造

```mermaid
graph LR
    subgraph "レベル進行"
        LV1[LV1<br/>常時アンロック]
        LV2[LV2<br/>LV1合格で解放]
        LV3[LV3<br/>LV2合格で解放]
        LV4[LV4<br/>LV3合格で解放]
    end

    LV1 -->|lv1_passed = true| LV2
    LV2 -->|lv2_passed = true| LV3
    LV3 -->|lv3_passed = true| LV4

    subgraph "進捗管理"
        GATE[GET /levels/status]
        PROG[(DynamoDB<br/>ai-levels-progress)]
    end

    GATE --> PROG
    PROG -->|lvN_passed| LV2 & LV3 & LV4
```

## 技術スタック

| レイヤー | 技術 | 備考 |
|---------|------|------|
| フロントエンド | HTML / CSS / Vanilla JS | SPA不要、静的ホスティング |
| CDN | CloudFront | S3オリジン、キャッシュ無効化対応 |
| API | API Gateway REST | CORS有効、29秒タイムアウト制限 |
| コンピュート | AWS Lambda (Python 3.12) | タイムアウト60秒 |
| AI | Amazon Bedrock Claude Sonnet 4.6 | グローバル推論プロファイル |
| DB | DynamoDB (PAY_PER_REQUEST) | results + progress 2テーブル |
| IaC | Serverless Framework | ローカルv4 / CI v3 |
| CI/CD | GitHub Actions | main push で自動デプロイ |
| テスト | pytest + Hypothesis | ユニット69件 + プロパティ19件 |

### なぜ Claude Sonnet 4.6 か

API Gatewayのハードリミットは29秒。Claude Opus 4.6では1リクエストあたり35〜44秒かかり、タイムアウトが頻発した。Claude Sonnet 4.6はMVPに十分な品質（テスト生成・採点・レビュー）を29秒以内で提供でき、コスト効率も良い。

## プロジェクト構成

```
.
├── backend/
│   ├── handlers/
│   │   ├── generate_handler.py      # LV1 出題エージェント
│   │   ├── grade_handler.py         # LV1 採点エージェント + レビュー呼出
│   │   ├── complete_handler.py      # LV1 完了保存
│   │   ├── lv2_generate_handler.py  # LV2 出題エージェント
│   │   ├── lv2_grade_handler.py     # LV2 採点エージェント + レビュー呼出
│   │   ├── lv2_complete_handler.py  # LV2 完了保存
│   │   ├── lv3_generate_handler.py  # LV3 出題エージェント
│   │   ├── lv3_grade_handler.py     # LV3 採点エージェント + レビュー呼出
│   │   ├── lv3_complete_handler.py  # LV3 完了保存
│   │   ├── lv4_generate_handler.py  # LV4 出題エージェント
│   │   ├── lv4_grade_handler.py     # LV4 採点エージェント + レビュー呼出
│   │   ├── lv4_complete_handler.py  # LV4 完了保存
│   │   └── gate_handler.py          # ゲーティング
│   └── lib/
│       ├── bedrock_client.py        # Bedrock共通クライアント (リトライ付き)
│       ├── reviewer.py              # LV1 レビューエージェント
│       ├── lv2_reviewer.py          # LV2 レビューエージェント
│       ├── lv3_reviewer.py          # LV3 レビューエージェント
│       ├── lv4_reviewer.py          # LV4 レビューエージェント
│       └── threshold_resolver.py    # 合格閾値リゾルバ (環境変数ベース)
├── frontend/
│   ├── index.html                   # トップページ
│   ├── lv1.html                     # LV1テスト画面
│   ├── lv2.html                     # LV2テスト画面
│   ├── lv3.html                     # LV3テスト画面
│   ├── lv4.html                     # LV4テスト画面
│   ├── favicon.ico
│   ├── css/style.css
│   └── js/
│       ├── config.js                # API Base URL設定
│       ├── api.js                   # API通信層
│       ├── app.js                   # LV1アプリロジック
│       ├── lv2-app.js               # LV2アプリロジック
│       ├── lv3-app.js               # LV3アプリロジック
│       ├── lv4-app.js               # LV4アプリロジック
│       └── gate.js                  # ゲーティングUI
├── tests/
│   ├── unit/                        # ユニットテスト (69件)
│   └── property/                    # プロパティベーステスト (19件)
├── .github/workflows/deploy.yml     # CI/CDパイプライン
├── serverless.yml                   # インフラ定義
└── requirements.txt                 # Python依存
```

## 設計上の特徴

- **認証なし**: session_id (UUID v4) ベースでセッション管理。ログイン不要でブラウザから即実行可能
- **3エージェント分業**: 出題・採点・レビューを独立したプロンプト/ハンドラで分離し、責務を明確化
- **リトライ付きBedrock呼出**: ThrottlingException等に対し指数バックオフで最大3回リトライ
- **コードフェンス除去**: LLMが ` ```json ``` ` で囲んで返すケースに対応する `strip_code_fence()` を実装
- **CORS全開放**: `Access-Control-Allow-Origin: *` で全ハンドラ統一
- **合格閾値の環境変数制御**: 各レベル (LV1〜LV4) の合格閾値を `PASS_THRESHOLD_LV{N}` 環境変数で設定可能。AIが返すスコアに対して閾値ベースで合否を上書きし、コード変更なしで閾値調整が可能（デフォルト: 30）
- **DynamoDB 2テーブル設計**: results (テスト結果詳細) と progress (レベル進捗) を分離

## ローカル開発

```bash
# 依存インストール
pip install -r requirements.txt

# テスト実行
pytest tests/ -v

# デプロイ (Serverless Framework v4)
serverless deploy --stage prod
```

## デプロイ

`main` ブランチへの push で GitHub Actions が自動実行:

1. **バックエンド**: `serverless deploy --stage prod` (Serverless Framework v3)
2. **フロントエンド**: `aws s3 sync frontend/ s3://ai-levels --delete` → CloudFrontキャッシュ無効化

必要な GitHub Secrets:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `SERVERLESS_ACCESS_KEY`
## 提案: 外部ログインシステムとのユーザー紐付け

### 背景

現在のシステムは `session_id` (UUID v4) で匿名セッション管理しているが、既存の外部システムにログイン機能とユーザー識別子が実装済みであれば、クエリパラメーター付きリンクを踏んでもらうだけでユーザー単位の回答保存が実現できる。

### 仕組み

```
外部システム → リンク生成 → AI Levels → DynamoDB にユーザー紐付け保存
```

1. 外部システム（ログイン済み）がユーザーごとにリンクを生成:
   ```
   https://d2iarskyjm3rk1.cloudfront.net/lv1.html?user_id=USR-12345
   ```

2. フロントエンドが `user_id` をクエリパラメーターから取得し、全APIリクエストに付与

3. バックエンドが `user_id` をDynamoDBのキーに組み込み、ユーザー単位で結果を保存

### データフロー

```mermaid
sequenceDiagram
    participant ExtSys as 外部システム<br/>(ログイン済み)
    participant Browser as ブラウザ
    participant FE as AI Levels<br/>フロントエンド
    participant API as API Gateway
    participant DB as DynamoDB

    ExtSys->>Browser: リンク生成<br/>lv1.html?user_id=USR-12345
    Browser->>FE: ページ読み込み
    FE->>FE: URLから user_id 取得
    FE->>API: POST /lv1/generate<br/>{session_id, user_id}
    API-->>FE: questions
    FE->>API: POST /lv1/grade<br/>{session_id, user_id, ...}
    API-->>FE: 採点結果
    FE->>API: POST /lv1/complete<br/>{session_id, user_id, ...}
    API->>DB: PK=USER#USR-12345<br/>SK=RESULT#lv1#session_id
    DB-->>FE: saved: true
```

### DynamoDB キー設計の変更

| 現在 | 変更後 |
|------|--------|
| `PK: SESSION#{session_id}` | `PK: USER#{user_id}` |
| `SK: RESULT#lv1` | `SK: RESULT#lv1#{session_id}` |

この変更により、同一ユーザーの複数回受験履歴をクエリで一括取得できる:

```python
# ユーザーの全受験履歴を取得
table.query(
    KeyConditionExpression="PK = :pk AND begins_with(SK, :sk)",
    ExpressionAttributeValues={
        ":pk": f"USER#{user_id}",
        ":sk": "RESULT#lv1"
    }
)
```

### 必要な変更箇所

| ファイル | 変更内容 |
|---------|---------|
| `frontend/js/app.js` | `URLSearchParams` で `user_id` を取得、APIリクエストに付与 |
| `frontend/js/api.js` | 各API呼び出しに `user_id` パラメーターを追加 |
| `backend/handlers/complete_handler.py` | PK を `USER#{user_id}` に変更、バリデーション追加 |
| `backend/handlers/gate_handler.py` | `user_id` ベースで進捗を取得 |

### セキュリティ上の注意

- `user_id` はクエリパラメーターで渡すだけなので、URLを知っていれば誰でもなりすまし可能
- MVP段階ではこれで十分だが、本番運用時は以下を検討:
  - 外部システムで署名付きトークン (HMAC / JWT) を生成し、AI Levels側で検証
  - トークンに有効期限を設定し、リプレイ攻撃を防止

## 提案: 採点結果返却API

### 概要

既存システムがAI Levelsの採点結果をプログラムで取得できるAPIを提供する。DynamoDBに保存済みの結果を、`user_id` または `session_id` をキーにJSON形式で返却する。

### エンドポイント設計

| メソッド | パス | 用途 |
|---------|------|------|
| `GET` | `/api/results/{user_id}` | ユーザーの全受験履歴を取得 |
| `GET` | `/api/results/{user_id}/latest` | ユーザーの最新結果のみ取得 |
| `GET` | `/api/results/session/{session_id}` | セッション単位で結果取得（現行互換） |

### リクエスト・レスポンス例

```
GET /api/results/USR-12345
Authorization: Bearer <api_key>
```

```json
{
  "user_id": "USR-12345",
  "results": [
    {
      "session_id": "382cc632-2f79-4a0f-bbfb-7c855fb30cb5",
      "level": "lv1",
      "total_score": 80,
      "final_passed": false,
      "completed_at": "2026-02-20T06:18:39.585758+00:00",
      "grades": [
        {"step": 1, "score": 30, "passed": true},
        {"step": 2, "score": 25, "passed": true},
        {"step": 3, "score": 25, "passed": false}
      ]
    }
  ],
  "count": 1
}
```

### 認証方式

外部システム間通信のため、APIキー認証を採用:

```
Authorization: Bearer sk-ai-levels-xxxxxxxxxxxx
```

- API Gatewayの使用量プランとAPIキーで実装（追加インフラ不要）
- 既存のCORS全開放エンドポイントとは別パスで分離

### データフロー

```mermaid
sequenceDiagram
    participant Ext as 既存システム
    participant APIGW as API Gateway<br/>(APIキー認証)
    participant Lambda as 結果取得 Lambda
    participant DB as DynamoDB<br/>ai-levels-results

    Ext->>APIGW: GET /api/results/USR-12345<br/>Authorization: Bearer <api_key>
    APIGW->>APIGW: APIキー検証
    APIGW->>Lambda: リクエスト転送
    Lambda->>DB: Query PK=USER#USR-12345<br/>begins_with(SK, RESULT#)
    DB-->>Lambda: 結果レコード群
    Lambda-->>APIGW: JSON レスポンス
    APIGW-->>Ext: 200 OK + 結果データ
```

### serverless.yml 追加分

```yaml
functions:
  getResults:
    handler: backend/handlers/results_handler.handler
    events:
      - http:
          path: api/results/{user_id}
          method: get
          private: true  # APIキー必須

  getLatestResult:
    handler: backend/handlers/results_handler.latest_handler
    events:
      - http:
          path: api/results/{user_id}/latest
          method: get
          private: true

  getSessionResult:
    handler: backend/handlers/results_handler.session_handler
    events:
      - http:
          path: api/results/session/{session_id}
          method: get
          private: true
```

### 必要な変更箇所

| ファイル | 変更内容 |
|---------|---------|
| `backend/handlers/results_handler.py` | 新規作成。DynamoDB Query で結果取得 |
| `serverless.yml` | 上記3エンドポイント追加 + 使用量プラン/APIキー定義 |
| `tests/unit/test_results_handler.py` | ユニットテスト |

### 前提条件

この結果返却APIは「ユーザー紐付け」提案（前セクション）の `USER#{user_id}` キー設計が実装済みであることが前提。現行の `SESSION#{session_id}` のみの場合は `/api/results/session/{session_id}` エンドポイントだけが利用可能。
