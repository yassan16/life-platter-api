"""設定値管理モジュール

pydantic-settingsを使用して環境変数を型安全に管理。
.envファイルから設定を読み込み、環境ごとの切り替えが可能。
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """アプリケーション設定

    環境変数または.envファイルから設定を読み込む。
    デフォルトは.env.localを読み込み、ローカル開発用。
    本番環境では環境変数で上書きされる。
    """

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str
    async_database_url: str | None = None

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # レート制限
    rate_limit_auth: str = "5/minute"

    # S3/AWS
    s3_bucket_name: str = ""
    aws_region: str = "ap-northeast-1"
    presigned_url_expires: int = 300
    max_image_size: int = 10485760  # 10MB
    cloudfront_domain: str = ""


@lru_cache
def get_settings() -> Settings:
    """設定のシングルトンインスタンスを取得"""
    return Settings()


settings = get_settings()
