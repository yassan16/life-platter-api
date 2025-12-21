# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# プロジェクト名
life_platter-api

## WHY（目的）
料理の自炊サポートを中心とした生活支援アプリ「life_platter」のバックエンドAPIサーバー。料理記録の管理、食材管理、レシピ管理機能を提供する。

## WHAT（技術スタック）
- 言語: Python 3.12
- フレームワーク: FastAPI + Uvicorn
- DB: MySQL 8.0 + SQLAlchemy (ORM) + PyMySQL (driver)
- インフラ: Docker (3サービス構成: MySQL + FastAPI + Nginx)
- Webサーバー: Nginx (リバースプロキシ)

## HOW（基本コマンド）
- 起動: `docker compose up -d`
- ログ確認: `docker compose logs -f app`
- 停止: `docker compose down`
- 再ビルド: `docker compose up -d --build`
- DB接続テスト: ブラウザで `http://localhost/db-check` にアクセス
- API仕様確認: ブラウザで `http://localhost/docs` にアクセス (Swagger UI)

## プロジェクト構成
```
life_platter-api/
├── main.py                     # FastAPIアプリのエントリーポイント
├── app/
│   ├── core/
│   │   └── database.py         # SQLAlchemy設定、セッション管理
│   └── features/               # 機能単位のモジュール構成
│       └── cooking/
│           └── router.py       # 料理関連エンドポイント
├── nginx/
│   └── default.conf            # Nginx設定 (ポート80 → app:8000)
├── docs/
│   └── docker-compose-startu-flow.md  # Docker起動フロー・アーキテクチャ詳細
├── docker-compose.yml          # サービス定義 (db, app, nginx)
├── Dockerfile                  # FastAPIコンテナ定義
└── requirements.txt            # Python依存パッケージ
```

## 作業ルール
- データベース接続は必ず `get_db()` 依存性注入を使用すること
- エンドポイントは機能ごとに `app/features/` 配下に配置
- ルーター登録は `main.py` で `app.include_router()` を使用
- 環境変数は `docker-compose.yml` で管理 (本番環境では `.env` 使用推奨)
- SQLログは開発時 `echo=True`、本番では `False` に設定

## 詳細ドキュメント
タスクに応じて以下を参照：
- Docker起動フロー・アーキテクチャ詳細: `docs/docker-compose-startu-flow.md`
  - データベース接続フロー
  - リクエストフロー (Nginx → FastAPI → MySQL)
  - Docker起動順序とシーケンス図
- APIエンドポイント仕様: `docs/api-endpoints.md`
  - 実装済みエンドポイント一覧
  - URL設計パターン
  - 今後実装予定のエンドポイント
