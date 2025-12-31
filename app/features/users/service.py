"""認証ビジネスロジック"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import REFRESH_TOKEN_EXPIRE_DAYS
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
)
from app.features.users.models import User, UserStatus
from app.features.users.repository import UserRepository, RefreshTokenRepository
from app.features.users.schemas import TokenResponse
from app.features.users.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotActiveError,
)


class AuthService:
    """認証サービス"""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.token_repo = RefreshTokenRepository(db)

    def register(self, username: str, email: str, password: str) -> TokenResponse:
        """
        ユーザー登録
        1. メールアドレス重複チェック
        2. パスワードハッシュ化
        3. ユーザー作成
        4. トークン発行
        """
        # メールアドレス重複チェック
        existing_user = self.user_repo.find_by_email(email)
        if existing_user:
            raise UserAlreadyExistsError()

        # パスワードハッシュ化してユーザー作成
        password_hash = hash_password(password)
        user = self.user_repo.create(username, email, password_hash)

        # トークン発行
        return self._issue_tokens(user)

    def login(self, email: str, password: str) -> TokenResponse:
        """
        ログイン
        1. ユーザー検索
        2. パスワード検証
        3. ステータスチェック
        4. トークン発行
        5. 最終ログイン日時更新
        """
        # ユーザー検索
        user = self.user_repo.find_by_email(email)
        if not user:
            raise InvalidCredentialsError()

        # パスワード検証
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        # ステータスチェック
        if user.status != UserStatus.active:
            raise UserNotActiveError()

        # 最終ログイン日時更新
        self.user_repo.update_last_login(user)

        # トークン発行
        return self._issue_tokens(user)

    def refresh(self, refresh_token_str: str) -> TokenResponse:
        """
        トークン更新
        1. JWTデコード・検証
        2. DBからトークン検索
        3. 古いトークン無効化
        4. 新しいトークン発行
        """
        # JWTデコード・検証
        payload = decode_token(refresh_token_str)
        if payload is None:
            raise InvalidTokenError()

        # リフレッシュトークンかどうかチェック
        if payload.get("type") != "refresh":
            raise InvalidTokenError()

        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError()

        # DBからトークン検索
        token_hash = hash_token(refresh_token_str)
        db_token = self.token_repo.find_by_hash(token_hash)
        if not db_token:
            raise InvalidTokenError()

        # ユーザー取得
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise InvalidTokenError()

        # ステータスチェック
        if user.status != UserStatus.active:
            raise UserNotActiveError()

        # 古いトークン無効化
        self.token_repo.revoke(db_token)

        # 新しいトークン発行
        return self._issue_tokens(user)

    def logout(self, user: User) -> None:
        """
        ログアウト
        - ユーザーの全リフレッシュトークンを無効化
        """
        self.token_repo.revoke_all_for_user(user.id)

    def _issue_tokens(self, user: User) -> TokenResponse:
        """トークン発行（内部メソッド）"""
        # アクセストークン生成
        access_token = create_access_token(user.id)

        # リフレッシュトークン生成
        refresh_token = create_refresh_token(user.id)

        # リフレッシュトークンをDBに保存
        token_hash = hash_token(refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        self.token_repo.create(user.id, token_hash, expires_at)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )
