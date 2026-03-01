# Bugfix Requirements Document

## Introduction

LV1クリア後にLV2ページへ遷移すると、ケーススタディの生成に失敗し、LV2を開始できないバグ。ゲートチェック（GET /levels/status）は200で成功するが、POST /lv2/generate の呼び出しが失敗し、フロントエンドの catch ブロックでエラーメッセージ「ケーススタディの生成に失敗しました。ネットワーク接続を確認してください。」が表示される。

根本原因の分析により、以下の問題が特定された：
- `bedrock_client.py` の `max_tokens: 2048` がLV2の4問ケーススタディ生成レスポンスに対して不十分であり、レスポンスが途中で切れて不完全なJSONとなり、バックエンドの `_parse_questions` でパースエラーが発生する
- `lv2_generate_handler.py` の `_parse_questions` バリデーションが厳格すぎ、LLMレスポンスの軽微なフォーマット差異でも500エラーを返す
- API Gateway の29秒タイムアウト制限に対して、LV2の複雑なプロンプト（4問の詳細ケーススタディ生成）のBedrock呼び出しが超過する可能性がある

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN LV2ケーススタディ生成のためにBedrock APIを呼び出す THEN `bedrock_client.py` の `max_tokens: 2048` ではLV2の4問分の詳細なケーススタディ（各問にstep, type, prompt, context を含む）のJSON出力に対してトークン数が不足し、レスポンスが途中で切断されて不完全なJSONが返される

1.2 WHEN Bedrockから返された不完全なJSONを `lv2_generate_handler.py` の `_parse_questions` でパースしようとする THEN `json.loads` が `JSONDecodeError` を発生させ、ハンドラが500エラーを返す

1.3 WHEN バックエンドが500エラーを返す THEN フロントエンド `lv2-app.js` の `start()` 関数の catch ブロックが実行され、「ケーススタディの生成に失敗しました。ネットワーク接続を確認してください。」というエラーメッセージが表示され、UIはローディング状態のまま停止する

1.4 WHEN LLMがLV2のケーススタディを生成する際にフォーマットが期待と微妙に異なる（例: contextがnull、typeの表記揺れ等） THEN `_parse_questions` の厳格なバリデーションが `ValueError` を発生させ、500エラーが返される

### Expected Behavior (Correct)

2.1 WHEN LV2ケーススタディ生成のためにBedrock APIを呼び出す THEN `max_tokens` はLV2の4問分の詳細なケーススタディJSON出力を完全に収容できる十分な値（4096以上）に設定されるべきであり、レスポンスが途中で切断されないこと

2.2 WHEN Bedrockからレスポンスを受信して `_parse_questions` でパースする THEN 完全なJSONが正常にパースされ、4問のケーススタディが正しく抽出・バリデーションされること

2.3 WHEN バックエンドが200で正常なレスポンスを返す THEN フロントエンド `lv2-app.js` の `start()` 関数が `data.questions` を正しく受け取り、最初のケーススタディ設問が画面に表示されること

2.4 WHEN LLMのレスポンスに軽微なフォーマット差異がある場合 THEN `_parse_questions` は可能な限り寛容にバリデーションし（例: contextがnullの場合は空文字列として扱う、typeの正規化等）、リカバリ可能なケースでは500エラーを返さないこと

### Unchanged Behavior (Regression Prevention)

3.1 WHEN LV1のテスト・ドリル生成（POST /lv1/generate）を呼び出す THEN システムは従来通り3問の設問を正常に生成し、200レスポンスを返すこと

3.2 WHEN LV2のゲートチェック（GET /levels/status）を呼び出す THEN システムは従来通りLV1合格状態に基づいてLV2のアンロック状態を正しく返すこと

3.3 WHEN LV2の回答採点（POST /lv2/grade）を呼び出す THEN システムは従来通り回答を採点し、スコアとフィードバックを正常に返すこと

3.4 WHEN LV2の完了保存（POST /lv2/complete）を呼び出す THEN システムは従来通り結果をDynamoDBに保存し、進捗を更新すること

3.5 WHEN LV3/LV4の生成・採点・完了エンドポイントを呼び出す THEN システムは従来通り正常に動作すること
