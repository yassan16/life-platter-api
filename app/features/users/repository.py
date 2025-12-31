"""DB操作リポジトリ"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.features.users.models import User, RefreshToken, UserStatus


class UserRepository:
    """ユーザーリポジトリ"""

    def __init__(self, db: Session):
        self.db = db

    def find_by_email(self, email: str) -> Optional[User]:
        """メールアドレスでユーザー検索（論理削除除外）"""
        return self.db.query(User).filter(
            User.email == email,
            User.deleted_at.is_(None),
        ).first()

    def find_by_id(self, user_id: str) -> Optional[User]:
        """IDでユーザー検索（論理削除除外）"""
        return self.db.query(User).filter(
            User.id == user_id,
            User.deleted_at.is_(None),
        ).first()

    def create(self, username: str, email: str, password_hash: str) -> User:
        """ユーザー作成"""
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            status=UserStatus.active,  # 登録時はアクティブ
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_last_login(self, user: User) -> None:
        """最終ログイン日時を更新"""
        user.last_login_at = datetime.now(timezone.utc)
        self.db.commit()


class RefreshTokenRepository:
    """リフレッシュトークンリポジトリ"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: str, token_hash: str, expires_at: datetime) -> RefreshToken:
        """リフレッシュトークン保存"""
        refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(refresh_token)
        self.db.commit()
        self.db.refresh(refresh_token)
        return refresh_token

    def find_by_hash(self, token_hash: str) -> Optional[RefreshToken]:
        """ハッシュでトークン検索（有効なもののみ）"""
        now = datetime.now(timezone.utc)
        return self.db.query(RefreshToken).filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        ).first()

    def revoke(self, refresh_token: RefreshToken) -> None:
        """トークン無効化"""
        refresh_token.revoked_at = datetime.now(timezone.utc)
        self.db.commit()

    def revoke_all_for_user(self, user_id: str) -> None:
        """ユーザーの全トークン無効化"""
        now = datetime.now(timezone.utc)
        self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        ).update({"revoked_at": now})
        self.db.commit()
