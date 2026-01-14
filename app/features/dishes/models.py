import uuid

from sqlalchemy import Column, String, DateTime, Date, Integer, ForeignKey, Index
from sqlalchemy.dialects.mysql import CHAR, TINYINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class DishCategory(Base):
    """料理カテゴリマスタテーブル"""
    __tablename__ = "dish_categories"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主キー（UUID）")
    name = Column(String(50), nullable=False, unique=True, comment="カテゴリ名")
    display_order = Column(Integer, nullable=False, default=0, comment="表示順序")
    created_at = Column(DateTime, server_default=func.now(), comment="作成日時")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新日時")
    deleted_at = Column(DateTime, nullable=True, comment="削除日時（論理削除）")

    # リレーション
    dishes = relationship("Dish", back_populates="category")


class Dish(Base):
    """料理テーブル"""
    __tablename__ = "dishes"
    __table_args__ = (
        Index("idx_dishes_user_cooked", "user_id", "cooked_at"),
        Index("idx_dishes_user_deleted", "user_id", "deleted_at"),
    )

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主キー（UUID）")
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=False, index=True, comment="ユーザーID")
    category_id = Column(CHAR(36), ForeignKey("dish_categories.id"), nullable=True, index=True, comment="カテゴリID")
    name = Column(String(200), nullable=False, comment="料理名")
    cooked_at = Column(Date, nullable=False, comment="作った日")
    created_at = Column(DateTime, server_default=func.now(), comment="作成日時")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新日時")
    deleted_at = Column(DateTime, nullable=True, comment="削除日時（論理削除）")

    # リレーション
    user = relationship("User", back_populates="dishes")
    category = relationship("DishCategory", back_populates="dishes")
    images = relationship("DishImage", back_populates="dish", cascade="all, delete-orphan")


class DishImage(Base):
    """料理画像テーブル"""
    __tablename__ = "dish_images"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment="主キー（UUID）")
    dish_id = Column(CHAR(36), ForeignKey("dishes.id", ondelete="CASCADE"), nullable=False, index=True, comment="料理ID")
    image_key = Column(String(200), nullable=False, comment="S3オブジェクトキー")
    display_order = Column(TINYINT, nullable=False, comment="表示順序（1-3）")
    created_at = Column(DateTime, server_default=func.now(), comment="作成日時")

    # リレーション
    dish = relationship("Dish", back_populates="images")
