# AI Levels - AIカリキュラム実行システム

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
            Gen[出題 Lambda<br/>POST /lv1/generate]
            Grade[採点+レビュー Lambda<br/>POST /lv1/grade]
            Complete[完了保存 Lambda<br/>POST /lv1/complete]
            Gate[ゲーティング Lambda<br/>GET /levels/status]
        end
    end

    subgraph "AWSサービス"
        Bedrock[Amazon Bedrock<br/>Claude Opus 4.6]
        DDB_R[DynamoDB<br/>ai-levels-results]
        DDB_P[DynamoDB<br/>ai-levels-progress]
    end

    Browser --> CF --> S3
    Browser -->|REST API| APIGW
    APIGW --> Gen
    APIGW --> Grade
    APIGW --> Complete
    APIGW --> Gate
    Gen --> Bedrock
    Grade --> Bedrock
    Complete --> DDB_R
    Complete --> DDB_P
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
    participant R as レビューエージェント
    participant BR as Bedrock Claude Opus 4.6
    participant DB as DynamoDB

    U->>FE: Lv1セッション開始
    FE->>API: POST /lv1/generate
    API->>TG: テスト生成リクエスト
    TG->>BR: プロンプト送信
    BR-->>TG: テスト・ドリル生成
    TG-->>FE: 設問データ（JSON）
    FE->>U: 設問表示

    loop 各ステップ（設問ごと）
        U->>FE: 回答入力・送信
        FE->>API: POST /lv1/grade
        API->>G: 採点リクエスト
        G->>BR: 回答評価
        BR-->>G: 合否判定 + スコア
        G->>R: 採点結果を渡す
        R->>BR: フィードバック生成
        BR-->>R: 解説・アドバイス
        R-->>FE: 採点結果 + フィードバック
        FE->>U: 結果・解説表示
    end

    U->>FE: 全ステップ完了
    FE->>API: POST /lv1/complete
    API->>DB: 完了レコード保存
    DB-->>FE: 保存成功
    FE->>U: 最終結果表示
```

## ゲーティング構造

```mermaid
graph LR
    subgraph "レベル進行"
        LV1[Lv1<br/>分業設計×依頼設計<br/>×品質担保×2ケース再現]
        LV2[Lv2<br/>🔒 ロック]
        LV3[Lv3<br/>🔒 ロック]
        LV4[Lv4<br/>🔒 ロック]
    end

    LV1 -->|合格| LV2
    LV2 -->|合格| LV3
    LV3 -->|合格| LV4

    style LV1 fill:#4CAF50,color:#fff
    style LV2 fill:#9E9E9E,color:#fff
    style LV3 fill:#9E9E9E,color:#fff
    style LV4 fill:#9E9E9E,color:#fff
```


Lv1に合格するとLv2がアンロックされる段階的進行方式。MVP段階ではLv1のみ実装済み、Lv2〜Lv4は将来拡張用のスロットとして存在。

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| フロントエンド | バニラ HTML/CSS/JS（フレームワーク不使用） |
| 配信 | CloudFront + S3 |
| API | API Gateway（REST） |
| コンピュート | AWS Lambda（Python 3.12） |
| AI モデル | Amazon Bedrock - Claude Opus 4.6（`global.anthropic.claude-opus-4-6-v1`） |
| データベース | DynamoDB（`ai-levels-results`, `ai-levels-progress`） |
| IaC | Serverless Framework v3 |
| CI/CD | GitHub Actions |

## プロジェクト構成

```
├── backend/
│   ├── handlers/
│   │   ├── generate_handler.py   # 出題エージェント
│   │   ├── grade_handler.py      # 採点+レビューエージェント
│   │   ├── complete_handler.py   # 完了レコード保存
│   │   └── gate_handler.py       # ゲーティング判定
│   └── lib/
│       ├── bedrock_client.py     # Bedrock呼び出し共通モジュール
│       └── reviewer.py           # レビューエージェント
├── frontend/
│   ├── index.html                # レベル選択画面
│   ├── lv1.html                  # Lv1カリキュラム実行画面
│   ├── css/style.css
│   └── js/
│       ├── app.js                # セッション管理・フロー制御
│       ├── api.js                # APIクライアント
│       └── gate.js               # ゲーティングロジック
├── tests/
│   ├── unit/                     # ユニットテスト（57件）
│   └── property/                 # プロパティベーステスト（13件）
├── serverless.yml
└── .github/workflows/deploy.yml
```

## 設計上の特徴

- **認証不要**: Lv1はログインなしでアクセス可能。セッションはブラウザの `sessionStorage` で管理
- **完了時のみDB保存**: 途中離脱ではDynamoDBへの書き込みが発生しない（ストレージコスト最適化）
- **1 APIコールで採点+レビュー**: `/lv1/grade` 内部でGrader → Reviewerを連鎖実行
- **指数バックオフリトライ**: Bedrock呼び出しのThrottlingExceptionに対して最大3回リトライ
- **プロパティベーステスト**: Hypothesisを使用した8つの正当性プロパティで形式的な品質保証

## ローカル開発

```bash
# 依存関係インストール
pip install -r requirements.txt

# テスト実行（70件）
python -m pytest tests/ -v
```

## デプロイ

`main` ブランチへのpushで GitHub Actions が自動実行:

1. バックエンド: `serverless deploy --stage prod`
2. フロントエンド: `aws s3 sync` → CloudFront キャッシュ無効化

必要なGitHub Secrets:
- `SERVERLESS_ACCESS_KEY`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
