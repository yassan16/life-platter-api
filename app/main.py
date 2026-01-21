import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text

from app.api import api_router
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

app = FastAPI()

# レート制限の設定
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """レート制限超過時のカスタムエラーハンドラー"""
    return JSONResponse(
        status_code=429,
        content={
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": "リクエスト回数が上限に達しました。しばらくお待ちください",
            "details": None,
        },
    )

# 環境変数の取得
# docker-compose.yml の environment: で設定した "DATABASE_URL" を読み込みます
# 中身: mysql+pymysql://user:password@db/life_platter_db
DATABASE_URL = os.getenv("DATABASE_URL")

# --- ルーターの統合 ---
# 全ての機能は /api プレフィックス配下に配置
# http://localhost/api/users/xxxxx
# http://localhost/api/dishes/xxxxx
app.include_router(api_router, prefix="/api")

# ルートパスへのアクセス (Hello World)
@app.get("/")
def read_root():
    """
    ブラウザで http://localhost/ にアクセスした時に呼ばれる
    """
    return {"message": "Hello, FastAPI is running!"}

# DB接続テスト用のパス
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
