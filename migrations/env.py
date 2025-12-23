import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy import engine_from_config

from alembic import context

# === 追加: プロジェクトルートをパスに追加 ===
# Dockerコンテナ内では /app がルート、ローカルではプロジェクトルート
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# === 追加: database.py から Base をインポート ===
from app.core.database import Base

# === 追加: 全モデルをインポート（autogenerateで検出するため） ===
from app.features import *

# Alembic Config オブジェクト
config = context.config

# === 追加: 環境変数から DATABASE_URL を取得 ===
database_url = os.getenv('DATABASE_URL')
if not database_url:
    raise ValueError("DATABASE_URL environment variable is not set")
config.set_main_option('sqlalchemy.url', database_url)

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
