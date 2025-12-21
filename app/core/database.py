import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. 環境変数から接続情報を取得
# docker-compose.yml で設定した "DATABASE_URL" がここに入ります
# 例: "mysql+pymysql://user:password@db/food_db"
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# 2. エンジン（接続の管理役）を作成
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # echo=True: 実行されるSQLをログに出力（開発中はTrueが便利）
    echo=True,
    # pool_pre_ping=True: 接続が生きているか確認してから使う（MySQLの切断エラー防止）
    pool_pre_ping=True,
)

# 3. セッションファクトリ（DBとの会話セッションを作る工場）を作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. モデルのベースクラスを作成
# すべてのテーブル定義（Model）はこのクラスを継承します
Base = declarative_base()


# 5. DBセッションの依存性注入（Dependency Injection）用関数
def get_db():
    """
    1リクエストごとにDBセッションを作成し、
    処理が終わったら必ず閉じるための関数
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
