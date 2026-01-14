# プロジェクト名
life_platter-api

## WHY（目的）
料理の自炊サポートを中心とした生活支援アプリ「life_platter」のバックエンドAPIサーバー。料理記録の管理、食材管理、レシピ管理機能を提供する。

## WHAT（技術スタック）
- 言語: Python 3.12
- フレームワーク: FastAPI + Uvicorn
- DB: MySQL 8.0 + SQLAlchemy (ORM) + PyMySQL (driver) + Alembic (マイグレーション)
- インフラ: Docker (3サービス構成: MySQL + FastAPI + Nginx)
- Webサーバー: Nginx (リバースプロキシ)

## HOW（基本コマンド）
基本的な操作コマンドは `docs/setup/commands.md` にまとめています。

## プロジェクト構成
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

### 機能モジュールの責務
| ファイル        | 責務                                             |
| --------------- | ------------------------------------------------ |
| `schemas.py`    | リクエスト/レスポンスのバリデーション (Pydantic) |
| `models.py`     | テーブル定義 (SQLAlchemy)                        |
| `repository.py` | DB操作の抽象化                                   |
| `service.py`    | ビジネスロジック                                 |
| `router.py`     | APIエンドポイント定義                            |
| `exceptions.py` | 機能固有の例外                                   |

## 作業ルール
- データベース接続は `app/core/deps.py` の依存性注入を使用すること
- エンドポイントは機能ごとに `app/features/` 配下に配置
- ルーター登録は `app/main.py` で `app.include_router()` を使用
- 新規テーブル作成時は `models.py` を作成後、Alembicでマイグレーション生成
- モデルは `app/features/__init__.py` でインポートを集約
- 環境変数は `docker-compose.yml` で管理 (本番環境では `.env` 使用推奨)
- SQLログは開発時 `echo=True`、本番では `False` に設定

## 詳細ドキュメント
タスクに応じて以下を参照：

### 機能仕様 (`docs/features/`)
- 認証機能: `docs/features/auth.md`
  - JWT + OAuth2 Password Flow
  - ログイン・ログアウト・トークン更新
  - リフレッシュトークン管理
  - レート制限
- 料理機能: `docs/features/dish/`
  - DB設計: `db-design.md`
    - dishes, dish_images, dish_categories テーブル設計
    - 削除・更新ポリシー（dishesは論理削除、dish_imagesは物理削除）
  - API仕様: `api-spec.md`
    - CRUD API（POST/GET/PUT/DELETE /dishes）
    - 画像の差分更新方式（images_to_add / images_to_delete）
    - カーソルベースページネーション
    - S3・DB連携のトランザクション管理
  - S3画像アップロード: `s3-image-upload.md`
    - Pre-signed URL方式
    - セキュリティ要件（IAM、CORS、ライフサイクル）
    - 障害パターンとリカバリ（孤立ファイル削除バッチ）
    - CloudFront経由の画像配信

### API共通仕様 (`docs/api/`)
- エンドポイント仕様: `docs/api/endpoints.md`
  - 実装済みエンドポイント一覧
  - URL設計パターン
  - 今後実装予定のエンドポイント
- エラーレスポンス仕様: `docs/api/error-handling.md`
  - 統一エラーレスポンス型 (error_code, message, details)
  - レスポンス例

### 環境構築・運用 (`docs/setup/`)
- 基本コマンド一覧: `docs/setup/commands.md`
  - Docker操作（起動・停止・ログ確認）
  - API動作確認（Swagger UI、DB接続テスト）
  - マイグレーション操作（Alembic）
  - データベース直接操作
- Docker起動フロー・アーキテクチャ詳細: `docs/setup/docker-compose-startup-flow.md`
  - データベース接続フロー
  - リクエストフロー (Nginx → FastAPI → MySQL)
  - Docker起動順序とシーケンス図

### データベース (`docs/database/`)
- Alembicマイグレーションセットアップ: `docs/database/migration-guide.md`
  - パッケージインストールから初期化まで
  - env.py・database.pyの非同期対応設定
  - モデル作成とマイグレーション実行フロー
  - トラブルシューティング
