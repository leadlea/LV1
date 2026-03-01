# バグ修正要件ドキュメント

## はじめに

LV2合格後にLV3が有効化され、「開始する」ボタンを押すとプロジェクトリーダーシップシナリオの生成が開始されるが、504タイムアウトエラーが発生しシナリオが表示されない。

根本原因は2つある:
1. `lv3_generate_handler.py`が`invoke_claude()`を呼ぶ際に`max_tokens`を明示指定しておらず、デフォルトの2048が使用される。LV3は5問生成（LV2は4問）でプロンプトも複雑なため、2048トークンではJSON出力が途中で切れる可能性が高い。
2. `bedrock_client.py`の`read_timeout=28秒`設定により、LV3の複雑なプロンプト（5ステップ、LV2より長い生成時間）でBedrockの応答が間に合わず、タイムアウトする。API Gatewayの29秒制限と合わせて504エラーとなる。

これらの組み合わせにより、`max_tokens`不足でJSON出力が切れる→パースエラー→リトライ→さらにタイムアウトという悪循環が発生する。

## バグ分析

### 現在の動作（不具合）

1.1 WHEN LV3シナリオ生成APIが呼ばれる THEN `invoke_claude()`に`max_tokens`が指定されず、デフォルトの2048トークンが使用されるため、5問分のJSON出力が途中で切れる可能性がある

1.2 WHEN LV3シナリオ生成でBedrockの応答に28秒以上かかる THEN `read_timeout=28秒`によりクライアント側でタイムアウトし、リトライ後にAPI Gatewayの29秒制限で504エラーが返される

1.3 WHEN LV3シナリオ生成でJSON出力が`max_tokens`不足により途中で切れる THEN パースエラーが発生しリトライが行われるが、リトライでも同じ`max_tokens`制限のため再度失敗し、最終的にタイムアウトする

1.4 WHEN LV3の`_parse_questions()`がBedrockレスポンスを処理する THEN `stop_reason`が`max_tokens`かどうかのチェックが行われず、切り詰められたレスポンスがそのままJSONパースに渡される

### 期待される動作（正しい動作）

2.1 WHEN LV3シナリオ生成APIが呼ばれる THEN `invoke_claude()`に`max_tokens=4096`が明示的に指定され、5問分のJSON出力が完全に生成される

2.2 WHEN LV3シナリオ生成でBedrockの応答に時間がかかる THEN `read_timeout`が十分な値（55秒）に設定され、Lambda timeout（60秒）内でBedrockの応答を待てる

2.3 WHEN LV3シナリオ生成でJSON出力が完全に生成される THEN パースエラーが発生せず、リトライによるタイムアウトの悪循環が起きない

2.4 WHEN LV3の`_parse_questions()`がBedrockレスポンスを処理する THEN `stop_reason`が`max_tokens`の場合は早期にエラーとして検出し、切り詰められたJSONのパースを試みない

### 変更されない動作（リグレッション防止）

3.1 WHEN LV2シナリオ生成APIが呼ばれる THEN システムは引き続き`max_tokens=3000`で正常にシナリオを生成する

3.2 WHEN LV1シナリオ生成APIが呼ばれる THEN システムは引き続き正常にシナリオを生成する

3.3 WHEN LV3シナリオ生成で正常にBedrockから応答が返る THEN システムは引き続き5問のバリデーション済みシナリオをフロントエンドに返す

3.4 WHEN Bedrockが`ThrottlingException`等のリトライ可能なエラーを返す THEN システムは引き続きエクスポネンシャルバックオフでリトライする

3.5 WHEN LV4シナリオ生成APIが呼ばれる THEN システムは引き続き正常にシナリオを生成する
