# 料理登録機能 - DB設計

## 概要

ユーザーが作った料理を記録する機能のデータベース設計。

## 要件

- 料理名
- 作った日
- 画像（最大3枚）
- user_idとの紐付け
- カテゴリとの紐付け（任意）

---

## テーブル設計

### dishes（料理テーブル）

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| id | CHAR(36) | PK | UUID |
| user_id | CHAR(36) | FK, INDEX | users.id |
| category_id | CHAR(36) | FK, NULL, INDEX | dish_categories.id |
| name | VARCHAR(200) | NOT NULL | 料理名 |
| cooked_at | DATE | NOT NULL | 作った日 |
| created_at | DateTime | NOT NULL, DEFAULT NOW() | 作成日時 |
| updated_at | DateTime | NOT NULL, DEFAULT NOW(), ON UPDATE NOW() | 更新日時 |
| deleted_at | DateTime | NULL | 論理削除日時 |

**インデックス:**
- PRIMARY KEY (id)
- INDEX (user_id, cooked_at DESC) - ユーザーの料理一覧取得用
- INDEX (user_id, deleted_at) - 論理削除を考慮したクエリ用
- INDEX (category_id)
- FOREIGN KEY (user_id) REFERENCES users(id)
- FOREIGN KEY (category_id) REFERENCES dish_categories(id)

**削除ポリシー:**
- 料理の削除: 論理削除（deleted_atに日時をセット）
- ユーザー削除時: アプリ層で該当ユーザーの料理を論理削除
- カテゴリ削除時: dishes.category_idはそのまま維持（参照先が論理削除でも問題なし）

### dish_images（料理画像テーブル）

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| id | CHAR(36) | PK | UUID |
| dish_id | CHAR(36) | FK, INDEX | dishes.id |
| image_key | VARCHAR(200) | NOT NULL | S3オブジェクトキー（例: dishes/{dish_id}/1.jpg） |
| display_order | TINYINT | NOT NULL | 表示順序（1-3） |
| created_at | DateTime | NOT NULL, DEFAULT NOW() | 作成日時 |

**インデックス:**
- PRIMARY KEY (id)
- INDEX (dish_id)
- FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE

**制約:**
- 1つの料理につき最大3枚（アプリ層で制御）

**更新・削除ポリシー:**
- 画像の更新: Delete-Insert方式（該当dish_idのレコードを全削除→新規挿入）
- 画像の削除: 物理削除（履歴不要のため）
- S3連携フロー:
  1. 新画像をS3の一時領域にアップロード（クライアント側）
  2. S3画像を正式パスにコピー（トランザクション外）
  3. DBトランザクション開始
  4. 既存レコードを物理削除
  5. 新レコードを挿入
  6. コミット
  7. 旧S3ファイル・一時ファイルを非同期で削除

> **Note**: S3操作をDBトランザクション外で実行する理由は、S3が2フェーズコミットに非対応のため。

### dish_categories（カテゴリマスタテーブル）

| カラム | 型 | 制約 | 説明 |
|--------|-----|------|------|
| id | CHAR(36) | PK | UUID |
| name | VARCHAR(50) | NOT NULL, UNIQUE | カテゴリ名 |
| display_order | INT | NOT NULL, DEFAULT 0 | 表示順序 |
| created_at | DateTime | NOT NULL, DEFAULT NOW() | 作成日時 |
| updated_at | DateTime | NOT NULL, DEFAULT NOW(), ON UPDATE NOW() | 更新日時 |
| deleted_at | DateTime | NULL | 論理削除日時 |

**インデックス:**
- PRIMARY KEY (id)
- UNIQUE (name)

**備考:**
- 全ユーザー共通のマスタテーブル
- 論理削除方式（削除時もdishes.category_idは維持）

**UNIQUE制約と論理削除の運用ルール:**
- `name`カラムにUNIQUE制約があるため、論理削除済みの同名カテゴリが存在すると新規作成できない
- 同名カテゴリを再登録する場合: 既存レコードの`deleted_at`をNULLに戻して復活させる
- アプリ層での処理フロー:
  1. 登録リクエスト受信
  2. 同名の論理削除済みレコードを検索
  3. 存在する場合 → `deleted_at = NULL`で復活
  4. 存在しない場合 → 新規レコード作成

---

## ER図

```
users
  │
  │ 1
  │
  ▼ N
dishes ────────── N:1 ────────── dish_categories
  │                              (共通マスタ)
  │ 1
  │
  ▼ N (max 3)
dish_images
```

---

## リレーション

| 親テーブル | 子テーブル | 関係 | 説明 |
|------------|------------|------|------|
| users | dishes | 1:N | ユーザーは複数の料理を登録可能 |
| dishes | dish_images | 1:N | 料理は最大3枚の画像を持つ |
| dish_categories | dishes | 1:N | カテゴリには複数の料理が属する（任意） |

---

## 削除・更新ポリシー一覧

| テーブル | 削除方式 | 更新方式 | 備考 |
|----------|----------|----------|------|
| dishes | 論理削除 | UPDATE | deleted_atで管理 |
| dish_images | 物理削除 | Delete-Insert | 履歴不要、S3と連携 |
| dish_categories | 論理削除 | UPDATE | 同名復活時はdeleted_at=NULLで復活 |

---

## 今後の拡張案（未実装）

必要に応じて以下を追加可能：

- `description` (TEXT) - 料理の説明・メモ
- `servings` (INT) - 何人前
- `rating` (TINYINT) - 自己評価（1-5）
- `recipe_id` (CHAR(36) FK) - レシピとの紐付け
