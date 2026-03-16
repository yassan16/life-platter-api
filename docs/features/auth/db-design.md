# 認証機能 DB設計

> 設計書（実装仕様）は [design.md](design.md) を参照。

## refresh_tokens テーブル

| カラム | 型 | 説明 |
|--------|------|------|
| id | CHAR(36) | UUID（主キー） |
| user_id | CHAR(36) | FK → users.id |
| token_hash | VARCHAR(255) | トークン値（ハッシュ化済み） |
| expires_at | DATETIME | 有効期限 |
| revoked_at | DATETIME | 無効化日時（nullable） |
| created_at | DATETIME | 作成日時 |

**インデックス**
- `token_hash`（トークン検索用）
- `user_id`（ユーザー別検索用）
