# 環境変数設定ガイド

## 概要

life_platter-apiでは、**pydantic-settings**を使用して環境変数を型安全に管理しています。

### 従来のos.getenv()との違い

| 項目 | os.getenv() | pydantic-settings |
|------|-------------|-------------------|
| 型安全性 | ❌ すべて文字列 | ✅ 型アノテーションで自動変換 |
| バリデーション | ❌ なし | ✅ 起動時に自動検証 |
| IDE補完 | ❌ なし | ✅ フル対応 |
| デフォルト値 | 引数で指定 | クラス定義で宣言的に管理 |
| .envファイル | 手動読み込み | 自動読み込み |

### メリット

1. **型安全性**: 環境変数を型付きオブジェクトとして扱える
   ```python
   # os.getenv()の場合
   expires = int(os.getenv("PRESIGNED_URL_EXPIRES", "300"))  # 手動変換

   # pydantic-settingsの場合
   expires = settings.presigned_url_expires  # 自動的にint型
   ```

2. **起動時バリデーション**: 設定エラーを実行前に検出
   ```python
   # 必須変数が未設定の場合、起動時にエラー
   ValidationError: DATABASE_URL environment variable is not set
   ```

3. **IDE補完**: 設定値へのアクセスが補完され、タイポを防止

4. **.envファイル自動読み込み**: 環境ごとの設定切り替えが容易

## ファイル構成

```
life_platter-api/
├── .env.example                    # テンプレート（Git管理 ✅）
├── .env.local                      # ローカル開発用（Git無視 ❌）
├── .env.production                 # 本番用（Git無視 ❌）
├── docker-compose.yml              # ベース設定
├── docker-compose.override.yml     # ローカル開発用（.env.localを使用）
├── docker-compose.prod.yml         # 本番用（.env.productionを使用）
└── app/core/config.py              # pydantic-settings設定
```

### 各ファイルの役割

- **`.env.example`**: 環境変数のテンプレート。Git管理され、新規開発者がコピーして使用
- **`.env.local`**: ローカル開発用。Git無視され、個人の開発環境に合わせて設定
- **`.env.production`**: 本番環境用。Git無視され、本番サーバーに直接配置
- **`app/core/config.py`**: pydantic-settingsの設定クラス定義

## 環境変数一覧

### Database（データベース）

| 変数名 | 説明 | 型 | デフォルト値 | 必須/任意 | 使用例 |
|--------|------|-----|-------------|----------|--------|
| `DATABASE_URL` | 同期DB接続URL | `str` | - | ✅ 必須 | `mysql+pymysql://user:password@db/life_platter_db` |
| `ASYNC_DATABASE_URL` | 非同期DB接続URL | `str \| None` | `None` | 任意 | `mysql+aiomysql://user:password@db/life_platter_db` |

**詳細説明**:
- **`DATABASE_URL`**: SQLAlchemyの同期エンジンで使用。形式: `mysql+pymysql://[user]:[password]@[host]/[database]`
- **`ASYNC_DATABASE_URL`**: 非同期エンジン用。未設定でも同期エンジンは動作可能

### JWT（認証・トークン管理）

| 変数名 | 説明 | 型 | デフォルト値 | 必須/任意 | 使用例 |
|--------|------|-----|-------------|----------|--------|
| `JWT_SECRET_KEY` | JWT署名用秘密鍵 | `str` | - | ✅ 必須 | `your-secret-key-change-in-production` |
| `JWT_ALGORITHM` | JWT署名アルゴリズム | `str` | `HS256` | 任意 | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | アクセストークン有効期限（分） | `int` | `30` | 任意 | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | リフレッシュトークン有効期限（日） | `int` | `7` | 任意 | `7` |

**詳細説明**:
- **`JWT_SECRET_KEY`**: トークン署名用の秘密鍵。**本番環境では必ず強力なランダム文字列を設定**
- **`JWT_ALGORITHM`**: 署名アルゴリズム。通常は`HS256`のまま使用
- **`ACCESS_TOKEN_EXPIRE_MINUTES`**: アクセストークンの有効期限（分単位）
- **`REFRESH_TOKEN_EXPIRE_DAYS`**: リフレッシュトークンの有効期限（日単位）

### Rate Limiting（レート制限）

| 変数名 | 説明 | 型 | デフォルト値 | 必須/任意 | 使用例 |
|--------|------|-----|-------------|----------|--------|
| `RATE_LIMIT_AUTH` | 認証APIのレート制限 | `str` | `5/minute` | 任意 | `5/minute` |

**詳細説明**:
- **`RATE_LIMIT_AUTH`**: 認証エンドポイント（ログイン等）のレート制限設定。形式: `回数/単位`

### AWS/S3（画像アップロード）

| 変数名 | 説明 | 型 | デフォルト値 | 必須/任意 | 使用例 |
|--------|------|-----|-------------|----------|--------|
| `S3_BUCKET_NAME` | S3バケット名 | `str` | `""` | 任意 | `life-platter-images` |
| `AWS_REGION` | AWSリージョン | `str` | `ap-northeast-1` | 任意 | `ap-northeast-1` |
| `PRESIGNED_URL_EXPIRES` | Pre-signed URL有効期限（秒） | `int` | `300` | 任意 | `300` |
| `MAX_IMAGE_SIZE` | 最大画像サイズ（バイト） | `int` | `10485760` | 任意 | `10485760` |
| `CLOUDFRONT_DOMAIN` | CloudFrontドメイン | `str` | `""` | 任意 | `https://d1234567890.cloudfront.net` |

**詳細説明**:
- **`S3_BUCKET_NAME`**: 画像保存先のS3バケット名。**空文字の場合はスタブモードで動作**（S3接続なし、開発用）
- **`AWS_REGION`**: S3バケットのリージョン
- **`PRESIGNED_URL_EXPIRES`**: Pre-signed URLの有効期限（秒単位）。デフォルト300秒（5分）
- **`MAX_IMAGE_SIZE`**: アップロード可能な最大画像サイズ。デフォルト10MB（10485760バイト）
- **`CLOUDFRONT_DOMAIN`**: CloudFront経由で画像配信する場合のドメイン。未設定の場合はS3直接URLを使用

## 環境別の設定例

### ローカル開発環境（`.env.local`）

```env
# === Database ===
DATABASE_URL=mysql+pymysql://user:password@db/life_platter_db

# === JWT ===
JWT_SECRET_KEY=local-dev-secret-key-change-in-production

# === AWS/S3 ===
# 空でスタブモード（S3接続なし）
S3_BUCKET_NAME=
AWS_REGION=ap-northeast-1
PRESIGNED_URL_EXPIRES=300
MAX_IMAGE_SIZE=10485760
CLOUDFRONT_DOMAIN=
```

**ポイント**:
- `S3_BUCKET_NAME`を空にすることで、AWS接続なしで開発可能
- `JWT_SECRET_KEY`は開発用の適当な値でOK

### 本番環境（`.env.production`）

```env
# === Database ===
DATABASE_URL=mysql+pymysql://user:SECURE_PASSWORD@rds-endpoint.ap-northeast-1.rds.amazonaws.com/life_platter_db

# === JWT ===
# 生成コマンド: python -c "import secrets; print(secrets.token_urlsafe(32))"
JWT_SECRET_KEY=<強力なランダム文字列>

# === AWS/S3 ===
S3_BUCKET_NAME=life-platter-images
AWS_REGION=ap-northeast-1
PRESIGNED_URL_EXPIRES=300
MAX_IMAGE_SIZE=10485760
CLOUDFRONT_DOMAIN=https://d1234567890.cloudfront.net
```

**ポイント**:
- `JWT_SECRET_KEY`は必ず強力なランダム文字列を生成して設定
- `DATABASE_URL`のパスワードは強力なものを使用
- `S3_BUCKET_NAME`に実際のバケット名を設定
- `CLOUDFRONT_DOMAIN`でCDN経由の高速配信を実現

## 環境切り替え方法

### ローカル開発

```bash
# docker-compose.override.yml が自動的に .env.local を読み込む
docker compose up
```

`docker-compose.override.yml`の設定:
```yaml
services:
  api:
    env_file:
      - .env.local  # ローカル開発用環境変数を読み込み
```

### 本番環境（EC2等）

```bash
# .env.production を使用
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

`docker-compose.prod.yml`の設定:
```yaml
services:
  api:
    env_file:
      - .env.production  # 本番用環境変数を読み込み
```

### 環境変数の優先順位

設定は以下の優先順位で適用されます（上ほど優先）:

1. **システム環境変数**（最優先）
   ```bash
   export DATABASE_URL=mysql+pymysql://...
   ```

2. **.envファイル**
   - `.env.local`（ローカル）
   - `.env.production`（本番）

3. **app/core/config.pyのデフォルト値**（最低優先）
   ```python
   jwt_algorithm: str = "HS256"
   ```

## セキュリティガイドライン

### JWT_SECRET_KEYの生成

本番環境では必ず強力なランダム文字列を生成して使用してください。

```bash
# 方法1: Pythonのsecretsモジュール（推奨）
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 方法2: OpenSSL
openssl rand -base64 32
```

出力例:
```
xK9jP2mN5vR8qW3tY6uI1oL4aS7dF0gH9bV5cX2zQ4e
```

この値を`.env.production`の`JWT_SECRET_KEY`に設定します。

### .env.productionのファイル権限

本番サーバーでは、`.env.production`の読み取り権限を所有者のみに制限します。

```bash
# 読み取り権限を所有者のみに制限
chmod 600 .env.production

# 所有者の確認
ls -la .env.production
# -rw------- 1 user user 256 Jan 18 12:00 .env.production
```

### Git管理の注意

| ファイル | Git管理 | 理由 |
|----------|---------|------|
| `.env.example` | ✅ 管理する | テンプレートとして共有 |
| `.env.local` | ❌ 管理しない | 個人の開発環境設定を含む |
| `.env.production` | ❌ 管理しない | 機密情報（パスワード、秘密鍵）を含む |

`.gitignore`で必ず除外されていることを確認:
```gitignore
# Environment files
.env.local
.env.production
```

### 本番環境でのベストプラクティス

1. **JWT_SECRET_KEY**
   - 最低32文字以上のランダム文字列を使用
   - 絶対にGitにコミットしない

2. **DATABASE_URL**
   - 強力なパスワードを使用（16文字以上、英数字+記号）
   - 本番DBは別の認証情報を使用

3. **ファイル権限**
   - `.env.production`は`chmod 600`で所有者のみ読み取り可能に

4. **環境変数管理サービスの検討**
   - AWS Secrets Manager
   - AWS Systems Manager Parameter Store
   - これらを使用すると、さらにセキュアな管理が可能

## トラブルシューティング

### エラー: "DATABASE_URL environment variable is not set"

**原因**: `.env`ファイルが読み込まれていない、または変数が未設定

**解決方法**:

```bash
# 1. .env.localが存在するか確認
ls -la .env.local

# 2. なければ.env.exampleからコピー
cp .env.example .env.local

# 3. DATABASE_URLが設定されているか確認
grep DATABASE_URL .env.local

# 4. 未設定の場合は編集して設定
# DATABASE_URL=mysql+pymysql://user:password@db/life_platter_db
```

### エラー: "JWT_SECRET_KEY environment variable is not set"

**原因**: `JWT_SECRET_KEY`が空文字または未設定

**解決方法**:

```bash
# 1. .env.localまたは.env.productionを編集
nano .env.local

# 2. JWT_SECRET_KEYに値を設定（空でない文字列）
# 開発環境
JWT_SECRET_KEY=local-dev-secret-key

# 本番環境（強力なランダム文字列を生成）
JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# 3. 確認
grep JWT_SECRET_KEY .env.local
```

### エラー: "validation error for Settings"

**原因**: 環境変数の型が不正（例: 数値を期待する変数に文字列を設定）

**詳細エラー例**:
```
validation error for Settings
PRESIGNED_URL_EXPIRES
  Input should be a valid integer, unable to parse string as an integer
```

**解決方法**:

```bash
# 数値型変数には数値を設定（引用符なし）
PRESIGNED_URL_EXPIRES=300  # ✅ 正しい
PRESIGNED_URL_EXPIRES="abc"  # ❌ エラー

# ブール値は "true" または "false" (小文字)
SOME_FLAG=true   # ✅ 正しい
SOME_FLAG=True   # ⚠️ 動作するが小文字推奨
SOME_FLAG=1      # ✅ 1 -> true, 0 -> false に変換される
```

### エラー: docker-compose.override.ymlが読み込まれない

**原因**: ファイル名が間違っている、またはyaml形式が不正

**解決方法**:

```bash
# 1. ファイル名を確認（正確に"docker-compose.override.yml"）
ls -la docker-compose.override.yml

# 2. yamlの構文チェック
docker compose config

# 3. エラーが表示された場合、インデントや構文を修正
# yaml-lintツールで検証も可能
```

### エラー: S3接続エラー

**原因**: `S3_BUCKET_NAME`が空でない場合、AWS認証情報が必要

**エラー例**:
```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**解決方法**:

```bash
# 開発環境: S3_BUCKET_NAMEを空に設定（スタブモード）
S3_BUCKET_NAME=

# 本番環境: AWS認証情報を設定

# 方法1: ~/.aws/credentialsファイルを作成
mkdir -p ~/.aws
cat > ~/.aws/credentials <<EOF
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
EOF

# 方法2: EC2のIAMロールを使用（推奨）
# EC2インスタンスにS3アクセス権限を持つIAMロールをアタッチ
```

### 環境変数が反映されない

**原因**: Dockerコンテナが古い設定を保持している

**解決方法**:

```bash
# 1. コンテナを完全に停止・削除して再起動
docker compose down
docker compose up -d

# 2. 設定が反映されたか確認（ログを確認）
docker compose logs api

# 3. 環境変数を直接確認
docker compose exec api env | grep DATABASE_URL
```

## 開発者向けメモ

### 新しい環境変数を追加する手順

1. **`app/core/config.py`のSettingsクラスに追加**

   ```python
   class Settings(BaseSettings):
       # 既存の設定...

       # 新しい変数を追加
       new_variable: str = "default_value"
       another_variable: int = 100
   ```

2. **`.env.example`に説明付きで追加**

   ```env
   # === 新しいセクション ===
   # 新しい変数の説明
   NEW_VARIABLE=default_value
   ANOTHER_VARIABLE=100
   ```

3. **`.env.local`と本番用に適切な値を設定**

   各開発者が`.env.local`を更新し、本番サーバーでは`.env.production`を更新。

4. **このドキュメントの変数一覧テーブルを更新**

   上記「環境変数一覧」セクションに新しい変数の行を追加。

### pydantic-settingsの型変換

pydantic-settingsは環境変数の文字列を自動的に型変換します。

| Pythonの型 | 環境変数の値 | 変換結果 |
|-----------|-------------|---------|
| `str` | `hello` | `"hello"` |
| `int` | `123` | `123` |
| `float` | `3.14` | `3.14` |
| `bool` | `true`, `1`, `yes` | `True` |
| `bool` | `false`, `0`, `no` | `False` |
| `str \| None` | 未設定 | `None` |
| `str \| None` | `value` | `"value"` |

**例**:

```python
# config.py
class Settings(BaseSettings):
    debug_mode: bool = False
    max_connections: int = 10
    api_timeout: float = 30.5
    optional_url: str | None = None
```

```env
# .env.local
DEBUG_MODE=true          # bool: True に変換
MAX_CONNECTIONS=50       # int: 50 に変換
API_TIMEOUT=15.5         # float: 15.5 に変換
# OPTIONAL_URL未設定      # None
```

### 環境変数名の命名規則

pydantic-settingsは、Pythonの属性名を大文字に変換して環境変数名として扱います。

| config.py | 環境変数名 |
|-----------|----------|
| `database_url` | `DATABASE_URL` |
| `jwt_secret_key` | `JWT_SECRET_KEY` |
| `s3_bucket_name` | `S3_BUCKET_NAME` |

スネークケース（`snake_case`）で定義すると、自動的に大文字（`UPPER_SNAKE_CASE`）の環境変数にマッピングされます。

### 設定のキャッシング

`app/core/config.py`では`@lru_cache`を使用して設定をキャッシュしています。

```python
@lru_cache
def get_settings() -> Settings:
    """設定のシングルトンインスタンスを取得"""
    return Settings()

settings = get_settings()
```

これにより、アプリケーション全体で同一の設定インスタンスを再利用し、パフォーマンスを向上させています。

## 参考リンク

- [pydantic-settings公式ドキュメント](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [FastAPI: Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/)
- [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/)
