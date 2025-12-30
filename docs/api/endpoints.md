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
- 機能ごとに prefix を設定: `/cooking/`, `/ingredients/`, `/recipes/`, etc.
- ルーター登録は `main.py` で `app.include_router()` を使用
- Swagger UI での分類には `tags` パラメータを使用

### 例
```python
# main.py
from app.features.cooking.router import router as cooking_router

app.include_router(
    cooking_router,
    prefix="/cooking",
    tags=["Cooking"]
)
```

---

## API ドキュメント (Swagger UI)

起動後、以下のURLでインタラクティブなAPI仕様を確認できます:
- **Swagger UI**: [http://localhost/docs](http://localhost/docs)
- **ReDoc**: [http://localhost/redoc](http://localhost/redoc)

---

## 今後実装予定のエンドポイント

### 料理関連
- `POST /cooking/` - 新規料理の登録
- `GET /cooking/{id}` - 料理詳細の取得
- `PUT /cooking/{id}` - 料理情報の更新
- `DELETE /cooking/{id}` - 料理の削除

### 食材関連
- `GET /ingredients/` - 食材一覧
- `POST /ingredients/` - 食材登録

### レシピ関連
- `GET /recipes/` - レシピ一覧
- `POST /recipes/` - レシピ登録
