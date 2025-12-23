import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


# === Base クラス（全モデルの基底） ===
class Base(DeclarativeBase):
    """SQLAlchemy 2.0 スタイルの基底クラス"""
    pass


# === 接続URL ===
DATABASE_URL = os.getenv("DATABASE_URL")  # 同期用: mysql+pymysql://...
ASYNC_DATABASE_URL = os.getenv("ASYNC_DATABASE_URL")  # 非同期用: mysql+aiomysql://...

# === 同期エンジン（Alembicマイグレーション用） ===
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
)

# 同期セッションファクトリ
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# === 非同期エンジン（アプリケーション実行用） ===
# 非同期エンジンは ASYNC_DATABASE_URL が設定されている場合のみ初期化
async_engine = None
AsyncSessionLocal = None

if ASYNC_DATABASE_URL:
    async_engine = create_async_engine(
        ASYNC_DATABASE_URL,
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
