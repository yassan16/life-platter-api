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

## HOW（開発ガイドライン）

### コマンド
基本的な操作コマンドは `docs/setup/commands.md` を参照。

### エンドポイント追加
- 機能ごとに `app/features/` 配下に配置
- ルーター登録は `app/main.py` で `app.include_router()` を使用

### データベース
- 接続は `app/core/deps.py` の依存性注入を使用
- 新規テーブル: `models.py` 作成後、Alembicでマイグレーション生成
- モデルは `app/features/__init__.py` でインポートを集約
- SQLログ: 開発時 `echo=True`、本番は `False`

### 環境変数
- `docker-compose.yml` で管理（本番環境では `.env` 使用推奨）

### ドキュメント
- Mermaidでフローチャートやシーケンス図を活用

## 詳細ドキュメント
詳細は `docs/README.md` を参照。

## 機能モジュールの責務
| ファイル        | 責務                                             |
| --------------- | ------------------------------------------------ |
| `schemas.py`    | リクエスト/レスポンスのバリデーション (Pydantic) |
| `models.py`     | テーブル定義 (SQLAlchemy)                        |
| `repository.py` | DB操作の抽象化                                   |
| `service.py`    | ビジネスロジック                                 |
| `router.py`     | APIエンドポイント定義                            |
| `exceptions.py` | 機能固有の例外                                   |
