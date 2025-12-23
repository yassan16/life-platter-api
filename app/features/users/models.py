import uuid
from enum import Enum as PyEnum

from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.dialects.mysql import CHAR
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
