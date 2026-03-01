# LV3アンロックバグ 修正設計

## 概要

LV2合格後にLV3がアンロックされないバグの修正設計。LV2完了ハンドラーがLV2専用セッションIDでプログレスを保存するが、ゲートハンドラーとフロントエンドはLV1セッションIDでプログレスを参照するため、LV2合格状態がLV3アンロック条件に反映されない。修正方針として、LV2完了時にLV1セッションIDのプログレスレコードも更新するようにする。

## 用語集

- **Bug_Condition (C)**: LV2合格時に `/lv2/complete` が呼ばれ、LV2セッションIDのプログレスのみ更新され、LV1セッションIDのプログレスが更新されない状態
- **Property (P)**: LV2合格時に `/lv2/complete` が呼ばれた場合、LV1セッションIDのプログレスレコードの `lv2_passed` も `true` に更新されること
- **Preservation**: LV1完了処理、ゲートハンドラーのレベル判定ロジック、フロントエンドのUI表示ロジックが変更されないこと
- **`_update_progress`**: `lv2_complete_handler.py` 内の関数。LV2完了時にプログレステーブルを更新する
- **`ai_levels_session`**: LV1セッションのsessionStorageキー。ゲートハンドラーが参照するプログレスレコードのセッションID
- **`ai_levels_lv2_session`**: LV2セッションのsessionStorageキー。LV2専用のセッションID

## バグ詳細

### 障害条件

LV2を合格して `/lv2/complete` が呼ばれた際、`lv2_complete_handler.py` の `_update_progress` がLV2セッションID（`ai_levels_lv2_session` から取得）でプログレスレコードを保存する。しかし、`gate_handler.py` と `gate.js` はLV1セッションID（`ai_levels_session` から取得）でプログレスを参照するため、LV2合格状態がLV3アンロック条件に反映されない。

**形式仕様:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type Lv2CompleteRequest
  OUTPUT: boolean

  lv2_session_id := input.session_id  // ai_levels_lv2_session から取得
  lv1_session_id := sessionStorage["ai_levels_session"].session_id

  RETURN input.final_passed == true
         AND lv2_session_id != lv1_session_id
         AND progressTable[lv1_session_id].lv2_passed == false
END FUNCTION
```

### 具体例

- ユーザーがLV1合格（`ai_levels_session` = `uuid-A`）→ LV2合格（`ai_levels_lv2_session` = `uuid-B`）→ `/lv2/complete` で `uuid-B` のプログレスに `lv2_passed: true` を保存 → `gate_handler` が `uuid-A` のプログレスを参照 → `lv2_passed: false` → LV3 `unlocked: false`
- 期待動作: `/lv2/complete` で `uuid-A` のプログレスにも `lv2_passed: true` を保存 → `gate_handler` が `uuid-A` のプログレスを参照 → `lv2_passed: true` → LV3 `unlocked: true`
- LV2不合格の場合: `final_passed: false` → `lv2_passed` は `false` のまま → LV3はアンロックされない（正しい動作）

## 期待される動作

### 保持要件

**変更されない動作:**
- LV1完了ハンドラー（`complete_handler.py`）の動作は一切変更しない
- ゲートハンドラー（`gate_handler.py`）のレベル判定ロジック（`_build_levels`）は変更しない
- フロントエンドのゲートロジック（`gate.js`）は変更しない
- LV1未合格ユーザーのLV2アンロック状態（`unlocked: false`）は変わらない
- LV2不合格時にLV3がアンロックされない動作は変わらない
- LV3以降の合格状態が既に存在する場合、それらの値は上書きされない

**スコープ:**
LV2合格時の `/lv2/complete` リクエスト処理のみが影響範囲。以下は影響を受けない:
- LV1完了処理（`/lv1/complete`）
- ゲートハンドラーの読み取りロジック（`/levels/status`）
- フロントエンドのUI表示ロジック（`gate.js`）
- LV3/LV4の完了処理

## 仮説的根本原因

バグの根本原因分析:

1. **セッションID不一致**: LV2フロントエンド（`lv2-app.js`）は `/lv2/complete` にLV2セッションID（`session.session_id`、`ai_levels_lv2_session` から取得）のみを送信する。LV1セッションID（`ai_levels_session`）は送信されない

2. **プログレス更新先の誤り**: `lv2_complete_handler.py` の `_update_progress` は受け取った `session_id`（= LV2セッションID）でプログレスレコードを作成・更新する。LV1セッションIDのプログレスレコードは更新されない

3. **ゲートハンドラーの参照先**: `gate_handler.py` と `gate.js` はLV1セッションID（`ai_levels_session`）でプログレスを参照する。LV2セッションIDのプログレスレコードは参照されない

結論: フロントエンドがLV1セッションIDをバックエンドに送信せず、バックエンドがLV1セッションIDのプログレスを更新しないことが根本原因。

## 正当性プロパティ

Property 1: 障害条件 - LV2合格時のLV1プログレス更新

_For any_ LV2完了リクエストで `final_passed` が `true` かつ `lv1_session_id` が有効なUUID v4である場合、修正後の `_update_progress` 関数はLV1セッションIDのプログレスレコードの `lv2_passed` を `true` に更新するものとする。

**Validates: Requirements 2.1, 2.2**

Property 2: 保持 - 既存プログレスの保全

_For any_ LV2完了リクエストにおいて、LV1セッションIDのプログレスレコードに既に存在する `lv1_passed`、`lv3_passed`、`lv4_passed` の値は、修正後の `_update_progress` 関数によって上書きされないものとする。

**Validates: Requirements 3.3, 3.5**

Property 3: 保持 - LV2不合格時の非アンロック

_For any_ LV2完了リクエストで `final_passed` が `false` の場合、修正後の関数はLV1セッションIDのプログレスレコードの `lv2_passed` を `true` に設定しないものとする。

**Validates: Requirements 3.4**

## 修正実装

### 必要な変更

根本原因分析に基づく修正:

**ファイル**: `frontend/js/lv2-app.js`

**関数**: `completeSession`

**変更内容**:
1. **LV1セッションIDの送信追加**: `ApiClient.lv2Complete` の呼び出し時に、`ai_levels_session` から取得したLV1セッションIDを `lv1_session_id` フィールドとして追加送信する

**ファイル**: `backend/handlers/lv2_complete_handler.py`

**関数**: `_update_progress`, `handler`

**変更内容**:
1. **LV1セッションIDの受け取り**: リクエストボディから `lv1_session_id` を取得する（オプショナルフィールド）
2. **LV1プログレスの更新**: `lv1_session_id` が有効なUUID v4の場合、LV1セッションIDのプログレスレコードの `lv2_passed` を更新する
3. **既存値の保持**: LV1プログレスレコードの `lv1_passed`、`lv3_passed`、`lv4_passed` は既存値を保持する
4. **LV2プログレスの維持**: 既存のLV2セッションIDでのプログレス保存は引き続き行う

## テスト戦略

### 検証アプローチ

テスト戦略は2段階: まず未修正コードでバグを再現するカウンター例を確認し、次に修正後のコードで正しい動作と既存動作の保持を検証する。

### 探索的障害条件チェック

**目的**: 修正前のコードでバグを再現し、根本原因分析を確認または反証する。

**テスト計画**: LV2完了リクエストをシミュレートし、LV1セッションIDのプログレスレコードが更新されないことを確認する。

**テストケース**:
1. **LV2合格テスト**: LV2セッションIDで `/lv2/complete` を呼び出し、LV1セッションIDのプログレスを確認（未修正コードで失敗）
2. **プログレス分離テスト**: LV2セッションIDとLV1セッションIDで別々のプログレスレコードが作成されることを確認

**期待されるカウンター例**:
- LV1セッションIDのプログレスレコードの `lv2_passed` が `false` のまま
- LV2セッションIDのプログレスレコードにのみ `lv2_passed: true` が保存される

### 修正チェック

**目的**: バグ条件が成立するすべての入力に対して、修正後の関数が期待される動作を生成することを検証する。

**擬似コード:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := lv2_complete_handler_fixed(input)
  ASSERT progressTable[input.lv1_session_id].lv2_passed == input.final_passed
END FOR
```

### 保持チェック

**目的**: バグ条件が成立しないすべての入力に対して、修正後の関数が元の関数と同じ結果を生成することを検証する。

**擬似コード:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT lv2_complete_handler_original(input) == lv2_complete_handler_fixed(input)
END FOR
```

**テストアプローチ**: プロパティベーステストを推奨。多数のテストケースを自動生成し、エッジケースを網羅的に検証できる。

**テスト計画**: 未修正コードでの既存動作を観察し、修正後もその動作が保持されることをプロパティベーステストで検証する。

**テストケース**:
1. **既存プログレス保持テスト**: LV1プログレスの `lv1_passed`、`lv3_passed`、`lv4_passed` が上書きされないことを検証
2. **LV2不合格時テスト**: `final_passed: false` の場合に `lv2_passed` が `true` にならないことを検証
3. **LV2プログレス維持テスト**: LV2セッションIDのプログレスレコードが引き続き正しく保存されることを検証

### ユニットテスト

- `lv2_complete_handler.py` の `_update_progress` がLV1セッションIDのプログレスを正しく更新するテスト
- `lv1_session_id` が無効または欠落している場合のフォールバック動作テスト
- `final_passed: false` の場合に `lv2_passed` が更新されないテスト

### プロパティベーステスト

- ランダムなセッションIDペアで `_update_progress` を実行し、LV1プログレスの `lv2_passed` が正しく設定されることを検証
- ランダムな既存プログレス状態で `_update_progress` を実行し、`lv1_passed`、`lv3_passed`、`lv4_passed` が保持されることを検証
- ランダムな `final_passed` 値で `_update_progress` を実行し、不合格時にLV3がアンロックされないことを検証

### 統合テスト

- LV1合格 → LV2合格 → `/levels/status` でLV3が `unlocked: true` になるフロー全体テスト
- LV1合格 → LV2不合格 → `/levels/status` でLV3が `unlocked: false` のままであるフローテスト
- フロントエンドが `lv1_session_id` を正しく送信することの検証
