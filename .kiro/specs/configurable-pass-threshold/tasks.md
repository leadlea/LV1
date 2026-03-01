# タスク: configurable-pass-threshold

## タスク1: Threshold_Resolver モジュールの作成

- [x] 1.1 `backend/lib/threshold_resolver.py` を作成し、`get_threshold(level: int) -> int` 関数を実装する。環境変数 `PASS_THRESHOLD_LV{level}` から値を読み取り、未設定時はデフォルト値30を返す。
- [x] 1.2 `get_threshold` にバリデーションロジックを追加する。非整数→デフォルト30、0未満→0に補正、100超→100に補正。不正値検出時はlogger.warningで警告を出力する。
- [x] 1.3 `resolve_passed(level: int, score: int) -> bool` 関数を実装する。`get_threshold(level)` で閾値を取得し、`score >= threshold` を返す。

## タスク2: serverless.yml に環境変数を追加

- [x] 2.1 `serverless.yml` の `provider.environment` セクションに `PASS_THRESHOLD_LV1: "30"`, `PASS_THRESHOLD_LV2: "30"`, `PASS_THRESHOLD_LV3: "30"`, `PASS_THRESHOLD_LV4: "30"` を追加する。

## タスク3: Grade Handler への統合

- [x] 3.1 `backend/handlers/grade_handler.py` で `resolve_passed` をインポートし、`_parse_grade_result` の後に `grade_result["passed"] = resolve_passed(level=1, score=grade_result["score"])` を追加する。
- [x] 3.2 `backend/handlers/lv2_grade_handler.py` で同様に `resolve_passed(level=2, ...)` を統合する。
- [x] 3.3 `backend/handlers/lv3_grade_handler.py` で同様に `resolve_passed(level=3, ...)` を統合する。
- [x] 3.4 `backend/handlers/lv4_grade_handler.py` で同様に `resolve_passed(level=4, ...)` を統合する。

## タスク4: プロパティベーステストの作成

- [x] 4.1 `tests/property/test_threshold_properties.py` を作成し、Property 1（閾値判定の正当性）のテストを実装する。任意のスコアと閾値に対して `resolve_passed` の結果が `score >= threshold` と一致することを検証する。
- [x] 4.2 Property 2（スコア保持）のテストを実装する。Grade Handler のレスポンスで score が AI の返した値と一致することを検証する。
- [x] 4.3 Property 3（閾値バリデーション結果の範囲保証）のテストを実装する。任意の環境変数値に対して `get_threshold` の結果が 0〜100 の整数であることを検証する。
- [x] 4.4 Property 4（不正値検出時の警告ログ）のテストを実装する。不正な値で警告ログが出力され、有効な値では出力されないことを検証する。
- [x] 4.5 Property 5（レベル別環境変数の正しい参照）のテストを実装する。各レベルが対応する環境変数を参照することを検証する。

## タスク5: ユニットテストの作成

- [x] 5.1 `tests/unit/test_threshold_resolver.py` を作成し、環境変数未設定時のデフォルト値30、非整数文字列のフォールバック、境界値（0, 100）の具体的なテストケースを実装する。
- [x] 5.2 各ハンドラが正しいレベル番号で `resolve_passed` を呼び出すことを検証するテストを追加する。
