---
name: api-conventions
description: life_platter-api のURL設計パターンとエラーレスポンス規約
---

# API規約

## URL設計パターン

### ルーティング規則

- 全てのAPIエンドポイントは `/api` プレフィックス配下に配置
- 統合ルーター `app/api/__init__.py` で機能ごとのルーターを集約
- 機能ごとに prefix を設定: `/api/users/`, `/api/dishes/`, `/api/ingredients/`, etc.
- Swagger UI での分類には `tags` パラメータを使用

### 実装例

```python
# app/api/__init__.py
from fastapi import APIRouter
from app.features.users.router import router as users_router
from app.features.dishes.router import router as dishes_router

api_router = APIRouter()
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(dishes_router, prefix="/dishes", tags=["Dishes"])

# app/main.py
from app.api import api_router

app.include_router(api_router, prefix="/api")
```

### エンドポイント命名規則

- リソース名は複数形のスネークケース: `/dishes`, `/ingredients`
- ネストは1段階まで: `/dishes/{id}/images`
- アクションが必要な場合はパスに動詞を使用: `/users/login`, `/users/refresh`

## エラーレスポンス規約

詳細は `@docs/api/error-handling.md` を参照。

共通フォーマット:
```json
{
  "error_code": "ERROR_CODE_STRING",
  "message": "ユーザー向けの説明（日本語）",
  "details": null
}
```
