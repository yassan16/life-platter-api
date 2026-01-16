# プロジェクト構成

```
life_platter-api/
├── alembic.ini                 # Alembic設定ファイル
├── migrations/                 # マイグレーションファイル (Alembic)
│   ├── versions/
│   └── env.py
├── app/
│   ├── main.py                 # FastAPIアプリのエントリーポイント
│   ├── core/                   # 機能横断の共通インフラ機能
│   │   ├── config.py              # 設定値管理
│   │   ├── database.py            # SQLAlchemy設定、セッション管理
│   │   ├── security.py            # 認証・認可
│   │   ├── exceptions.py          # 共通例外
│   │   └── deps.py                # 共通の依存性注入
│   └── features/               # 機能単位のモジュール構成
│       ├── __init__.py            # 全モデルのインポート集約
│       ├── users/
│       │   ├── schemas.py            # リクエスト/レスポンス (Pydantic)
│       │   ├── models.py             # SQLAlchemyモデル
│       │   ├── repository.py         # DB操作
│       │   ├── service.py            # ビジネスロジック
│       │   ├── router.py             # APIエンドポイント
│       │   └── exceptions.py         # 機能固有例外
│       └── items/
│           └── ...
├── nginx/
│   └── default.conf            # Nginx設定 (ポート80 → app:8000)
├── docs/                       # ドキュメント
├── docker-compose.yml          # サービス定義 (db, app, nginx)
├── Dockerfile                  # FastAPIコンテナ定義
└── requirements.txt            # Python依存パッケージ
```
