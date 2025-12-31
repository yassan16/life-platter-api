import uuid
from enum import Enum as PyEnum

from sqlalchemy import Column, String, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class UserStatus(PyEnum):
    """ユーザーステータス"""
    active = "active"           # 通常
    provisional = "provisional" # 仮登録
    banned = "banned"           # 凍結


class User(Base):
    """ユーザーテーブル"""
    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主キー（UUID）")
    username = Column(String(100), nullable=False, comment="表示名（ニックネーム）")
    email = Column(String(255), nullable=False, unique=True, index=True, comment="メールアドレス（ログインID）")
    email_verified_at = Column(DateTime, nullable=True, comment="メール確認完了日時")
    password_hash = Column(String(255), nullable=False, comment="ハッシュ化されたパスワード")
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.provisional, comment="ステータス")
    last_login_at = Column(DateTime, nullable=True, comment="最終ログイン日時")
    created_at = Column(DateTime, server_default=func.now(), comment="作成日時")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新日時")
    deleted_at = Column(DateTime, nullable=True, comment="削除日時（論理削除）")

    # リレーション
    refresh_tokens = relationship("RefreshToken", back_populates="user")


class RefreshToken(Base):
    """リフレッシュトークンテーブル"""
    __tablename__ = "refresh_tokens"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主キー（UUID）")
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True, comment="ユーザーID")
    token_hash = Column(String(255), nullable=False, index=True, comment="トークンハッシュ（SHA-256）")
    expires_at = Column(DateTime, nullable=False, comment="有効期限")
    revoked_at = Column(DateTime, nullable=True, comment="無効化日時")
    created_at = Column(DateTime, server_default=func.now(), comment="作成日時")

    # リレーション
    user = relationship("User", back_populates="refresh_tokens")
