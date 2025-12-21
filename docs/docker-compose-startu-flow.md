# 🚀 FastAPI + Docker 開発環境構築 & 起動ガイド

このドキュメントは、Mac (Colima) 環境における FastAPI, MySQL, Nginx の Docker 構築手順と、起動時の内部フローをまとめたものです。

---

## 🛠 1. 開発環境構築フロー

### 1-1. 前提環境 (Mac + Colima)
Docker Desktopの代わりにColimaを使用する場合、DB安定化のためにリソースを確保して起動します。

### 1-2. ディレクトリ構成
プロジェクトルート (`life_platter-api`) の構成は以下の通りです。

```text
life_platter-api/
├── nginx/
│   └── default.conf     # Webサーバー設定
├── app/                 # 機能ベース構成
│   ├── core/
│   │   └── database.py  # SQLAlchemy設定、セッション管理
│   └── features/        # 機能単位のモジュール構成
│       └── cooking/
│           └── router.py  # 料理関連エンドポイント
├── main.py              # FastAPIアプリのエントリーポイント
├── requirements.txt     # ライブラリ一覧
├── Dockerfile           # FastAPI用コンテナ定義
└── docker-compose.yml   # 全体の構成定義
```

### 1-3. 主要ファイルの記述内容

#### Dockerfile
```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /src

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Nginx経由のため8000番で待機
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

#### docker-compose.yml
```yaml
version: '3.8'

services:
  db:
    image: mysql:8.0
    container_name: life_platter_db
    ports:
      - "3306:3306"
    environment:
      MYSQL_DATABASE: life_platter_db
      MYSQL_USER: user
      MYSQL_PASSWORD: password
      MYSQL_ROOT_PASSWORD: root_password
    volumes:
      - db_data:/var/lib/mysql

  app:
    build: .
    container_name: life_platter_app
    volumes:
      - .:/app
    environment:
      DATABASE_URL: mysql+pymysql://user:password@db/life_platter_db
    depends_on:
      - db

  nginx:
    image: nginx:latest
    container_name: life_platter_nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - app

volumes:
  db_data:
```

---

## 🏗 2. アーキテクチャ

### データベース接続フロー
1. `docker-compose.yml` の `environment` で `DATABASE_URL` を設定
2. `database.py` が `os.getenv("DATABASE_URL")` で環境変数を取得
3. SQLAlchemy の `create_engine()` でコネクションプールを作成
4. `get_db()` 関数で各リクエストごとにセッションを提供

**重要**: ホスト名は `db` (Dockerサービス名) を使用。`localhost` ではない。

### 接続文字列
```
mysql+pymysql://user:password@db/life_platter_db
```
- ユーザー名: `user`
- パスワード: `password`
- ホスト: `db` (docker-composeサービス名)
- データベース名: `life_platter_db`

### リクエストフロー
```
ブラウザ → Nginx:80 → FastAPI:8000 → MySQL:3306
```

Nginxがリバースプロキシとして動作し、外部からのHTTPリクエストをFastAPIアプリケーションに転送します。FastAPIは必要に応じてMySQLデータベースにアクセスします。

---

## 🌊 3. 起動シーケンス詳細フロー

コマンド実行からリクエスト受付開始までの内部処理フローです。

**起動コマンド:**
```bash
docker compose up --build
```

### Docker起動順序
1. MySQL コンテナ起動 (3306ポート待機)
2. FastAPI コンテナ起動 (`depends_on: db`)
3. Nginx コンテナ起動 (`depends_on: app`)

### シーケンス図

```mermaid
sequenceDiagram
    participant User as 👨‍💻 User
    participant Docker as 🐳 Docker Engine
    participant DB as 🗄️ MySQL
    participant App as 🐍 FastAPI
    participant Nginx as 🌐 Nginx

    User->>Docker: docker compose up

    rect rgb(240, 248, 255)
        note right of Docker: 【Phase 1: 準備】
        Docker->>Docker: ネットワーク作成
        Docker->>Docker: イメージビルド & ボリューム作成
    end

    rect rgb(255, 250, 240)
        note right of Docker: 【Phase 2: DB起動】
        Docker->>DB: コンテナ起動 (Start)
        activate DB
        note over DB: ポート3306待機<br>(初期化処理開始)
    end

    rect rgb(240, 255, 240)
        note right of Docker: 【Phase 3: App起動】
        note over Docker: "depends_on: db" 検知
        Docker->>App: コンテナ起動 (Start)
        activate App
        App->>App: CMD実行 (uvicorn)
        App->>DB: 接続試行
        note over App: ポート8000待機
    end

    rect rgb(230, 230, 250)
        note right of Docker: 【Phase 4: Nginx起動】
        note over Docker: "depends_on: app" 検知
        Docker->>Nginx: コンテナ起動 (Start)
        activate Nginx
        Nginx->>Docker: 名前解決 "http://app はどこ？"
        Docker-->>Nginx: IPアドレス返答
        note over Nginx: ポート80待機 (Ready!)
    end

    User->>Nginx: アクセス (http://localhost)
    Nginx->>App: 転送
```

### ステップ解説

1.  **Phase 1: インフラ準備**
    * Dockerが仮想ネットワークを作成し、コンテナ同士が名前（`db`, `app`）で通信できるようにする。

2.  **Phase 2: DB (MySQL) 起動**
    * `depends_on` の制約がないため最初に起動。
    * コンテナ起動直後はデータ初期化処理が走るため、数秒間は接続を受け付けない場合がある。

3.  **Phase 3: App (FastAPI) 起動**
    * Dockerが「DBコンテナ開始」を検知して起動。
    * `CMD` コマンドでUvicornサーバーが立ち上がる。
    * 起動時にDBへの接続を試みる。

4.  **Phase 4: Nginx 起動**
    * Dockerが「Appコンテナ開始」を検知して起動。
    * 設定ファイル (`default.conf`) を読み込み、`http://app:8000` への転送準備を完了する。
    * ポート80を開放し、ブラウザからのアクセス待ち状態になる。

---

## ✅ 4. 動作確認

ブラウザで以下のURLにアクセスして確認します。

* **API稼働確認:** [http://localhost/](http://localhost/)
* **DB接続テスト:** [http://localhost/db-check](http://localhost/db-check)
* **APIドキュメント:** [http://localhost/docs](http://localhost/docs)
