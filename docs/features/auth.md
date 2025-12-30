# 認証機能仕様書

## 概要
JWT + OAuth2 Password Flow によるログイン処理を実装する。

---

## 要件

| 項目 | 仕様 |
|------|------|
| 認証方式 | JWT + OAuth2 Password Flow |
| アクセストークン有効期限 | 30分 |
| リフレッシュトークン有効期限 | 7日 |
| リフレッシュトークン保存 | DBに保存（無効化可能） |
| レート制限 | slowapi（カスタム設定可能） |
| 実装方式 | 同期（def） |

---

## エンドポイント

| メソッド | パス | 説明 | 認証 | レート制限 |
|---------|------|------|:----:|:---------:|
| POST | `/auth/login` | ログイン | 不要 | あり |
| POST | `/auth/refresh` | トークン更新 | 不要 | あり |
| POST | `/auth/logout` | ログアウト | 必要 | なし |
| GET | `/users/me` | 現在のユーザー情報 | 必要 | なし |

---

## リクエスト・レスポンス仕様

### POST /auth/login

**リクエスト**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**レスポンス（成功: 200）**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**エラーレスポンス（401）**
```json
{
  "error_code": "INVALID_CREDENTIALS",
  "message": "メールアドレスまたはパスワードが正しくありません",
  "details": null
}
```

**エラーレスポンス（429: レート制限）**
```json
{
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "リクエスト回数が上限に達しました。しばらくお待ちください",
  "details": null
}
```

---

### POST /auth/refresh

**リクエスト**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**レスポンス（成功: 200）**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**エラーレスポンス（401）**
```json
{
  "error_code": "INVALID_TOKEN",
  "message": "トークンが無効または期限切れです",
  "details": null
}
```

---

### POST /auth/logout

**ヘッダー**
```
Authorization: Bearer <access_token>
```

**レスポンス（成功: 200）**
```json
{
  "message": "ログアウトしました"
}
```

---

### GET /users/me

**ヘッダー**
```
Authorization: Bearer <access_token>
```

**レスポンス（成功: 200）**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "太郎",
  "email": "taro@example.com",
  "status": "active"
}
```

**エラーレスポンス（401）**
```json
{
  "error_code": "INVALID_TOKEN",
  "message": "トークンが無効または期限切れです",
  "details": null
}
```

---

## データベース設計

### refresh_tokens テーブル

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

---

## 設定値

| 設定項目 | 環境変数 | デフォルト値 |
|---------|---------|-------------|
| JWT秘密鍵 | `JWT_SECRET_KEY` | （必須） |
| JWTアルゴリズム | - | HS256 |
| アクセストークン有効期限 | - | 30分 |
| リフレッシュトークン有効期限 | - | 7日 |
| ログインレート制限 | - | 5回/分 |

---

## セキュリティ考慮事項

1. **パスワード**: bcryptでハッシュ化して保存
2. **リフレッシュトークン**: DBにハッシュ化して保存、無効化可能
3. **レート制限**: ログイン・リフレッシュエンドポイントに適用
4. **トークン検証**: 署名検証 + 有効期限チェック
5. **ログアウト**: リフレッシュトークンをDBで無効化

---

## ファイル構成

```
app/
├── core/
│   ├── config.py          # 設定値管理
│   └── security.py        # JWT・パスワード処理
└── features/
    └── users/
        ├── models.py      # User, RefreshToken モデル
        ├── schemas.py     # Pydantic スキーマ
        ├── repository.py  # DB操作
        ├── service.py     # ビジネスロジック
        └── router.py      # エンドポイント定義
```
