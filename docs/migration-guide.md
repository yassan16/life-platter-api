# Alembic マイグレーション セットアップガイド

このドキュメントは、FastAPIプロジェクトでAlembicを使用したデータベースマイグレーションをセットアップする手順をまとめています。

---

## 概要

### 目的
- SQLAlchemyモデルの変更をデータベーススキーマに反映する
- マイグレーション履歴を管理し、ロールバックを可能にする
- チーム開発でのスキーマ変更を安全に共有する

### 前提条件
- Docker環境が構築済み
- MySQL 8.0 + FastAPI + Nginx の構成
- SQLAlchemy がインストール済み

### 接続方式の設計

| 用途 | ドライバ | 理由 |
|------|----------|------|
| マイグレーション実行 | `pymysql`（同期） | Alembic自体が同期設計、安定性重視 |
| アプリケーション実行 | `aiomysql`（非同期） | FastAPIの非同期性能を活かす |

### 全体フロー

```mermaid
flowchart TD
    A[STEP 1: パッケージインストール] --> B[STEP 2: Alembic初期化]
    B --> C[STEP 3: alembic.ini設定]
    C --> D[STEP 4: env.py設定]
    D --> E[STEP 5: database.py非同期対応]
    E --> F[STEP 6: モデル作成]
    F --> G[STEP 7: マイグレーション実行]
```

---

## STEP 1: パッケージインストール

### 1-1. requirements.txt に追加

```txt
alembic
aiomysql
greenlet
```

| パッケージ | 用途 |
|-----------|------|
| `alembic` | マイグレーション管理ツール |
| `aiomysql` | MySQL非同期ドライバ |
| `greenlet` | 非同期処理の互換性サポート |

### 1-2. コンテナを再ビルド

```bash
docker compose down
docker compose up -d --build
```

### 1-3. インストール確認

```bash
docker compose exec app pip list | grep -E "alembic|aiomysql"
```

---

## STEP 2: Alembic 初期化

### 2-1. 初期化コマンドの実行

```bash
docker compose exec app alembic init migrations
```

### 2-2. 生成されるファイル構成

```
life_platter-api/
├── alembic.ini              # Alembic設定ファイル（自動生成）
└── migrations/              # マイグレーションディレクトリ（自動生成）
    ├── env.py               # マイグレーション実行環境
    ├── script.py.mako       # マイグレーションテンプレート
    ├── README                # 説明ファイル
    └── versions/            # マイグレーションファイル格納先
```

### 2-3. 各ファイルの役割

| ファイル | 役割 |
|----------|------|
| `alembic.ini` | 接続先DB、スクリプト場所などの設定 |
| `env.py` | マイグレーション実行時の環境設定 |
| `script.py.mako` | 新規マイグレーションファイルのテンプレート |
| `versions/` | 生成されたマイグレーションファイルを格納 |

---

## STEP 3: alembic.ini 設定

### 3-1. sqlalchemy.url をコメントアウト

`alembic.ini` を編集し、データベースURLの行をコメントアウトします（環境変数から取得するため）。

**変更前:**
```ini
sqlalchemy.url = driver://user:pass@localhost/dbname
```

**変更後:**
```ini
# sqlalchemy.url = driver://user:pass@localhost/dbname
```

### 3-2. script_location の確認

以下の設定が正しいことを確認します。

```ini
script_location = migrations
```

---

## STEP 4: migrations/env.py の設定

### 4-1. env.py を以下の内容に置き換え

```python
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy import engine_from_config

from alembic import context

# === 追加: プロジェクトルートをパスに追加 ===
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# === 追加: database.py から Base をインポート ===
from app.core.database import Base

# === 追加: 全モデルをインポート（autogenerateで検出するため） ===
from app.features import *

# Alembic Config オブジェクト
config = context.config

# === 追加: 環境変数から DATABASE_URL を取得 ===
config.set_main_option('sqlalchemy.url', os.getenv('DATABASE_URL'))

# ロギング設定
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# === 変更: target_metadata を Base.metadata に設定 ===
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """オフラインモードでマイグレーションを実行"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """オンラインモードでマイグレーションを実行（同期接続）"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### 4-2. 設定のポイント

| 設定項目 | 説明 |
|----------|------|
| `sys.path.insert(...)` | プロジェクトルートをPythonパスに追加 |
| `from app.core.database import Base` | モデルの基底クラスをインポート |
| `from app.features import *` | 全モデルをインポート（autogenerate用） |
| `config.set_main_option(...)` | 環境変数からDB接続URLを取得 |
| `target_metadata = Base.metadata` | Alembicにモデル情報を渡す |

---

## STEP 5: database.py の非同期対応

### 5-1. app/core/database.py を更新

同期エンジン（マイグレーション用）と非同期エンジン（アプリ実行用）の両方を保持します。

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# === 接続URL ===
DATABASE_URL = os.getenv("DATABASE_URL")  # 同期用: mysql+pymysql://...
ASYNC_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL")  # 非同期用: mysql+aiomysql://...

# === Base クラス（全モデルの基底） ===
Base = declarative_base()

# === 同期エンジン（Alembicマイグレーション用） ===
engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
)

# 同期セッションファクトリ
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# === 非同期エンジン（アプリケーション実行用） ===
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
)

# 非同期セッションファクトリ
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# === 依存性注入（同期） ===
def get_db():
    """同期セッションを提供（従来のエンドポイント用）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# === 依存性注入（非同期） ===
async def get_async_db():
    """非同期セッションを提供（非同期エンドポイント用）"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

### 5-2. docker-compose.yml に環境変数を追加

```yaml
services:
  app:
    environment:
      DATABASE_URL: mysql+pymysql://user:password@db/life_platter_db
      ASYNC_DATABASE_URL: mysql+aiomysql://user:password@db/life_platter_db
```

---

## STEP 6: モデル作成

### 6-1. モデルファイルの作成例

**`app/features/cooking/models.py`**

```python
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.core.database import Base


class Cooking(Base):
    """料理テーブル"""
    __tablename__ = "cookings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="料理名")
    category = Column(String(100), comment="カテゴリ")
    description = Column(Text, comment="説明")
    created_at = Column(DateTime, server_default=func.now(), comment="作成日時")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新日時")
```

### 6-2. モデルのインポート集約

**`app/features/__init__.py`**

```python
"""
全モデルをここでインポート
Alembicの autogenerate がモデルを検出するために必要
"""

from app.features.cooking.models import Cooking

# 新しいモデルを追加したら、ここにもインポートを追加する
# from app.features.users.models import User
# from app.features.ingredients.models import Ingredient
```

---

## STEP 7: マイグレーション実行フロー

### 7-1. マイグレーションファイルの作成

```bash
# 自動生成（モデルの変更を検出）
docker compose exec app alembic revision --autogenerate -m "create cookings table"
```

生成されるファイル:
```
migrations/versions/xxxxxxxxxxxx_create_cookings_table.py
```

### 7-2. 生成されたファイルの確認

必ず内容を確認し、必要に応じて編集します。

```python
def upgrade() -> None:
    op.create_table(
        'cookings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        # ...
    )

def downgrade() -> None:
    op.drop_table('cookings')
```

### 7-3. マイグレーションの実行

```bash
# 最新バージョンまで適用
docker compose exec app alembic upgrade head
```

### 7-4. ロールバック

```bash
# 1つ前に戻す
docker compose exec app alembic downgrade -1

# 完全にロールバック（初期状態に戻す）
docker compose exec app alembic downgrade base
```

### 7-5. 履歴確認

```bash
# 現在のリビジョンを確認
docker compose exec app alembic current

# 履歴を表示
docker compose exec app alembic history

# 詳細な履歴
docker compose exec app alembic history --verbose
```

### 7-6. オフラインモード（SQL文生成）

Alembicの「オフライン」モードは、**データベースに接続せずにSQL文を生成する**機能です（インターネット接続の有無ではありません）。

#### オンラインモード vs オフラインモード

| モード | 動作 | 用途 |
|--------|------|------|
| **オンラインモード**（通常） | データベースに直接接続してマイグレーションを実行 | 開発環境での通常のマイグレーション |
| **オフラインモード** | SQL文を生成するだけ（DBは変更しない） | 本番環境での事前確認、DBA向けSQL出力 |

#### オフラインモードの用途

1. **本番環境での事前確認**
   - 実際にどのようなSQLが実行されるか確認したい
   - データベースを変更せずに安全に検証できる

2. **DBAによる手動実行が必要な場合**
   - 開発者がデータベース変更権限を持たない環境
   - SQL文を出力してDBAに渡し、手動で実行してもらう

3. **CI/CDでのSQL文検証**
   - プルリクエスト時にどんなSQLが実行されるかレビュー

#### 使用例

```bash
# オンラインモード（通常）- データベースに接続して実行
docker compose exec app alembic upgrade head

# オフラインモード - SQL文を標準出力に表示
docker compose exec app alembic upgrade head --sql

# SQL文をファイルに保存
docker compose exec app alembic upgrade head --sql > migration.sql
```

**出力例**:
```sql
-- Running upgrade  -> a1b2c3d4e5f6

CREATE TABLE cookings (
    id INTEGER NOT NULL AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL COMMENT '料理名',
    category VARCHAR(100) COMMENT 'カテゴリ',
    description TEXT COMMENT '説明',
    created_at DATETIME DEFAULT now() COMMENT '作成日時',
    updated_at DATETIME DEFAULT now() COMMENT '更新日時',
    PRIMARY KEY (id)
);

INSERT INTO alembic_version (version_num) VALUES ('a1b2c3d4e5f6');
```

#### 注意点

- オフラインモードでは実際のデータベースは変更されません
- SQL文を手動実行した場合は、`alembic_version` テーブルも手動で更新する必要があります

---

## マイグレーションフロー図

```mermaid
flowchart TD
    subgraph 開発フロー
        A[モデル作成/変更] --> B[features/__init__.py に追加]
        B --> C["alembic revision --autogenerate"]
        C --> D[生成ファイルを確認]
        D --> E["alembic upgrade head"]
    end

    subgraph ロールバックフロー
        F[問題発生] --> G["alembic downgrade -1"]
        G --> H[コード修正]
        H --> I["alembic upgrade head"]
    end
```

---

## トラブルシューティング

### エラー: `Target database is not up to date`

**原因**: マイグレーションが未適用

**対処**:
```bash
docker compose exec app alembic upgrade head
```

---

### エラー: `Can't locate revision identified by 'xxxx'`

**原因**: マイグレーションファイルが見つからない

**対処**:
```bash
# 現在のDBの状態を確認
docker compose exec db mysql -u user -ppassword life_platter_db -e "SELECT * FROM alembic_version;"

# 必要に応じてリセット
docker compose exec app alembic stamp head
```

---

### エラー: `ModuleNotFoundError: No module named 'app'`

**原因**: Pythonパスが正しく設定されていない

**対処**: `migrations/env.py` の先頭で以下を確認

```python
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

---

### エラー: モデルの変更が検出されない

**原因**: モデルが `app/features/__init__.py` でインポートされていない

**対処**: `app/features/__init__.py` にインポートを追加

```python
from app.features.cooking.models import Cooking
from app.features.new_feature.models import NewModel  # 追加
```

---

### エラー: `Table 'xxx' already exists`

**原因**: テーブルが既に存在している

**対処**:
```bash
# 現在のリビジョンを強制設定
docker compose exec app alembic stamp head
```

---

### エラー: `Connection refused`

**原因**: DBコンテナが起動していない

**対処**:
```bash
# コンテナの状態確認
docker compose ps

# DBコンテナが起動するまで待つ
docker compose up -d
docker compose logs -f db
```

---

## ベストプラクティス

1. **マイグレーションファイルは必ずコミット**: チーム全員で共有
2. **`--autogenerate` を使用**: 手動より安全
3. **実行前に内容を確認**: 自動生成でも間違いがある場合がある
4. **`downgrade()` も正しく実装**: ロールバック可能にする
5. **本番環境では必ずバックアップを取る**
6. **1つのマイグレーションに複数の変更を含めすぎない**: 小さく頻繁に
