# 基本コマンド一覧

このドキュメントは、life_platter-api の開発で使用する基本的なコマンドをまとめています。

---

## Docker 操作

### 起動・停止

```bash
# 起動（バックグラウンド）
docker compose up -d

# 停止
docker compose down

# 再ビルド
docker compose up -d --build
```

### ログ確認

```bash
# アプリケーションのログをリアルタイム表示
docker compose logs -f app

# すべてのサービスのログを表示
docker compose logs -f
```

### コンテナ管理

```bash
# 起動中のすべてのコンテナを停止
docker stop $(docker ps -q)

# docker-compose.yml の環境だけを完全に消したい場合
docker-compose down --rmi all --volumes --remove-orphans

# PC内のDockerを（起動中も含めて）全消去・リセットしたい場合
docker system prune -a --volumes
```

⚠️ **注意**: `docker system prune -a --volumes` は全てのDockerデータが削除されます。他のプロジェクトにも影響があるため注意してください。

---

## API 動作確認

### ブラウザでアクセス

- **DB接続テスト**: [http://localhost/db-check](http://localhost/db-check)
- **API仕様確認 (Swagger UI)**: [http://localhost/docs](http://localhost/docs)
- **API仕様確認 (ReDoc)**: [http://localhost/redoc](http://localhost/redoc)
- **ヘルスチェック**: [http://localhost/](http://localhost/)

---

## データベース マイグレーション (Alembic)

### マイグレーションファイルの作成

```bash
# 自動生成（推奨）
docker compose exec app alembic revision --autogenerate -m "メッセージ"

# 手動作成
docker compose exec app alembic revision -m "メッセージ"
```

### マイグレーションの実行

```bash
# 最新バージョンまで適用
docker compose exec app alembic upgrade head

# 1つ前に戻す
docker compose exec app alembic downgrade -1

# 完全にロールバック
docker compose exec app alembic downgrade base
```

### マイグレーション履歴の確認

```bash
# 現在のリビジョンを確認
docker compose exec app alembic current

# 履歴を表示
docker compose exec app alembic history

# 詳細な履歴
docker compose exec app alembic history --verbose
```

---

## データベース直接操作

```bash
# MySQLに接続
docker compose exec db mysql -u user -ppassword life_platter_db

# SQLファイルの実行
docker compose exec db mysql -u user -ppassword life_platter_db < backup.sql
```

---

## その他の便利なコマンド

### コンテナ内に入る

```bash
# アプリケーションコンテナに入る
docker compose exec app bash

# DBコンテナに入る
docker compose exec db bash
```

### Pythonパッケージのインストール

```bash
# requirements.txtに追加後
docker compose exec app pip install -r requirements.txt

# または再ビルド
docker compose up -d --build
```

### 開発時のリロード

- Dockerfile で `--reload` オプションが有効なため、コード変更時は自動的にリロードされます
- ただし、requirements.txt の変更時は再ビルドが必要です
