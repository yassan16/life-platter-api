from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings


# === Base クラス（全モデルの基底） ===
class Base(DeclarativeBase):
    """SQLAlchemy 2.0 スタイルの基底クラス"""
    pass


# === 同期エンジン（Alembicマイグレーション用） ===
engine = create_engine(
    settings.database_url,
    echo=True,
    pool_pre_ping=True,
)

# 同期セッションファクトリ
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# === 非同期エンジン（アプリケーション実行用） ===
# 非同期エンジンは ASYNC_DATABASE_URL が設定されている場合のみ初期化
async_engine = None
AsyncSessionLocal = None

if settings.async_database_url:
    async_engine = create_async_engine(
        settings.async_database_url,
        echo=True,
        pool_pre_ping=True,
    )

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
    if AsyncSessionLocal is None:
        raise RuntimeError("ASYNC_DATABASE_URL is not configured")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
