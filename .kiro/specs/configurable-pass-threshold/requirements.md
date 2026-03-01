# 要件定義書

## はじめに

現在のAIカリキュラムシステムでは、各レベル（LV1〜LV4）の合否判定がAIモデル（Claude）に完全に委ねられており、コード内に数値的な合格閾値が存在しない。そのため、テスト期間中に合格ラインを一時的に下げたい場合でもコード変更が必要になる。

本機能は、各レベルの合格閾値を環境変数で設定可能にし、AIが返すスコアに対して閾値ベースで合否を上書きできるようにする。これにより、コードやロジックを変更せずに閾値の調整が可能になる。

## 用語集

- **Grade_Handler**: 各レベルの回答を採点するLambdaハンドラ（grade_handler.py, lv2_grade_handler.py, lv3_grade_handler.py, lv4_grade_handler.py）
- **Threshold_Resolver**: 環境変数から合格閾値を読み取り、スコアに基づいて合否を判定するモジュール
- **Pass_Threshold**: 合格に必要な最低スコア（0〜100の整数）。スコアがこの値以上であれば合格とする
- **AI_Grade_Result**: AIモデルが返す採点結果（passed: bool, score: 0〜100）
- **Serverless_Config**: serverless.ymlの環境変数設定

## 要件

### 要件1: レベル別合格閾値の環境変数定義

**ユーザーストーリー:** 運用担当者として、各レベルの合格閾値を環境変数で設定したい。テスト期間中にコード変更なしで閾値を調整できるようにするため。

#### 受け入れ基準

1. THE Serverless_Config SHALL 環境変数 PASS_THRESHOLD_LV1, PASS_THRESHOLD_LV2, PASS_THRESHOLD_LV3, PASS_THRESHOLD_LV4 を定義する
2. THE Serverless_Config SHALL 各閾値のデフォルト値を30に設定する
3. WHEN 環境変数が設定されていない場合, THE Threshold_Resolver SHALL デフォルト値30を合格閾値として使用する

### 要件2: スコアベースの合否判定オーバーライド

**ユーザーストーリー:** 運用担当者として、AIの合否判定をスコアと閾値の比較で上書きしたい。閾値を下げることでテスト期間中に次のレベルへ進めるようにするため。

#### 受け入れ基準

1. WHEN AIがスコアを返した場合, THE Grade_Handler SHALL スコアが Pass_Threshold 以上であれば passed を true に設定する
2. WHEN AIがスコアを返した場合, THE Grade_Handler SHALL スコアが Pass_Threshold 未満であれば passed を false に設定する
3. THE Grade_Handler SHALL AIが返した元の passed 値ではなく、閾値ベースの判定結果をレスポンスに含める
4. THE Grade_Handler SHALL AIが返した score 値はそのままレスポンスに含める

### 要件3: 閾値バリデーション

**ユーザーストーリー:** 運用担当者として、不正な閾値が設定された場合にシステムが安全に動作することを保証したい。設定ミスによるシステム障害を防ぐため。

#### 受け入れ基準

1. IF 環境変数の値が整数に変換できない場合, THEN THE Threshold_Resolver SHALL デフォルト値30を使用する
2. IF 環境変数の値が0未満の場合, THEN THE Threshold_Resolver SHALL 値を0に補正する
3. IF 環境変数の値が100を超える場合, THEN THE Threshold_Resolver SHALL 値を100に補正する
4. THE Threshold_Resolver SHALL 不正な値を検出した場合にログに警告を出力する

### 要件4: 全レベルへの一貫した適用

**ユーザーストーリー:** 運用担当者として、LV1〜LV4の全レベルで同じ閾値メカニズムが適用されることを保証したい。レベル間で動作が異なることを防ぐため。

#### 受け入れ基準

1. THE Grade_Handler SHALL LV1の採点時に PASS_THRESHOLD_LV1 環境変数の値を閾値として使用する
2. THE Grade_Handler SHALL LV2の採点時に PASS_THRESHOLD_LV2 環境変数の値を閾値として使用する
3. THE Grade_Handler SHALL LV3の採点時に PASS_THRESHOLD_LV3 環境変数の値を閾値として使用する
4. THE Grade_Handler SHALL LV4の採点時に PASS_THRESHOLD_LV4 環境変数の値を閾値として使用する
5. THE Threshold_Resolver SHALL 全レベルで共通のバリデーションロジックを使用する
