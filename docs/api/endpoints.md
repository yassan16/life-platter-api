# API エンドポイント仕様

このドキュメントは、life_platter-api のエンドポイント一覧と設計パターンを記載しています。

---

## 現在実装済みエンドポイント

### ヘルスチェック
- **エンドポイント**: `GET /`
- **説明**: API稼働確認用のヘルスチェック
- **レスポンス例**:
  ```json
  {
    "message": "Hello, FastAPI is running!"
  }
  ```

### データベース接続確認
- **エンドポイント**: `GET /db-check`
- **説明**: MySQL データベースへの接続確認
- **レスポンス例** (成功時):
  ```json
  {
    "status": "success",
    "db_response": 1
  }
  ```
- **レスポンス例** (失敗時):
  ```json
  {
    "status": "error",
    "message": "エラーメッセージ"
  }
  ```

### 料理一覧取得
- **エンドポイント**: `GET /cooking/`
- **説明**: 料理データの一覧を取得（現在はダミーデータ）
- **レスポンス例**:
  ```json
  [
    {
      "id": 1,
      "name": "カレーライス",
      "category": "洋食"
    },
    {
      "id": 2,
      "name": "肉じゃが",
      "category": "和食"
    }
  ]
  ```

---

## URL設計パターン

### ルーティング規則
- 全てのAPIエンドポイントは `/api` プレフィックス配下に配置
- 統合ルーター `app/api/__init__.py` で機能ごとのルーターを集約
- 機能ごとに prefix を設定: `/api/users/`, `/api/dishes/`, `/api/ingredients/`, etc.
- Swagger UI での分類には `tags` パラメータを使用

### 例
```python
# app/api/__init__.py
from fastapi import APIRouter
from app.features.users.router import router as users_router
from app.features.dishes.router import router as dishes_router

api_router = APIRouter()
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(dishes_router, prefix="/dishes", tags=["Dishes"])

# main.py
from app.api import api_router

app.include_router(api_router, prefix="/api")
```

---

## API ドキュメント (Swagger UI)

起動後、以下のURLでインタラクティブなAPI仕様を確認できます:
- **Swagger UI**: [http://localhost/docs](http://localhost/docs)
- **ReDoc**: [http://localhost/redoc](http://localhost/redoc)

---

## 今後実装予定のエンドポイント

### 食材関連
- `GET /api/ingredients/` - 食材一覧
- `POST /api/ingredients/` - 食材登録

### レシピ関連
- `GET /api/recipes/` - レシピ一覧
- `POST /api/recipes/` - レシピ登録
