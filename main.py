import os
from fastapi import FastAPI
from sqlalchemy import create_engine, text

app = FastAPI()

# 1. 環境変数の取得
# docker-compose.yml の environment: で設定した "DATABASE_URL" を読み込みます
# 中身: mysql+pymysql://user:password@db/life_platter_db
DATABASE_URL = os.getenv("DATABASE_URL")

# 2. ルートパスへのアクセス (Hello World)
@app.get("/")
def read_root():
    """
    ブラウザで http://localhost/ にアクセスした時に呼ばれる
    """
    return {"message": "Hello, FastAPI is running!"}

# 3. DB接続テスト用のパス
@app.get("/db-check")
def db_check():
    """
    ブラウザで http://localhost/db-check にアクセスした時に呼ばれる
    実際にDBにSQLを投げて接続確認を行う
    """
    try:
        # DBエンジンの作成（接続設定）
        # echo=True にすると実行されたSQLがログに出るためデバッグに便利
        engine = create_engine(DATABASE_URL, echo=True)

        # 実際に接続して "SELECT 1" という単純なクエリを実行
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            
            # 成功すれば {"status": "success", "db_response": 1} が返る
            return {"status": "success", "db_response": result.scalar()}

    except Exception as e:
        # 失敗したらエラーメッセージを返す
        return {"status": "error", "message": str(e)}
