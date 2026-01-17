"""料理機能のPydanticスキーマ"""

from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_validator


# === リクエストスキーマ ===


class ImageInput(BaseModel):
    """画像入力（登録時）"""
    image_key: str = Field(..., min_length=1, max_length=200)
    display_order: int = Field(..., ge=1, le=3)


class ImageAddInput(BaseModel):
    """画像追加入力（更新時）"""
    image_key: str = Field(..., min_length=1, max_length=200)
    # display_orderはサーバー側で自動採番


class DishCreateRequest(BaseModel):
    """料理登録リクエスト"""
    name: str = Field(..., min_length=1, max_length=200)
    cooked_at: date
    category_id: Optional[str] = None
    images: Optional[List[ImageInput]] = Field(default=None, max_length=3)

    @field_validator("images")
    @classmethod
    def validate_display_order_unique(cls, v):
        """display_orderの重複チェック"""
        if v is None:
            return v
        orders = [img.display_order for img in v]
        if len(orders) != len(set(orders)):
            raise ValueError("display_orderが重複しています")
        return v


class DishUpdateRequest(BaseModel):
    """料理更新リクエスト（差分更新方式）"""
    name: str = Field(..., min_length=1, max_length=200)
    cooked_at: date
    category_id: Optional[str] = None
    images_to_add: Optional[List[ImageAddInput]] = Field(default=None, max_length=3)
    images_to_delete: Optional[List[str]] = Field(default=None, max_length=3)


# === レスポンススキーマ ===


class CategoryResponse(BaseModel):
    """カテゴリレスポンス"""
    id: str
    name: str

    model_config = {"from_attributes": True}


class ImageResponse(BaseModel):
    """画像レスポンス"""
    id: str
    image_url: str
    display_order: int


class DishResponse(BaseModel):
    """料理詳細レスポンス"""
    id: str
    name: str
    cooked_at: date
    category: Optional[CategoryResponse] = None
    images: List[ImageResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DishListItemResponse(BaseModel):
    """料理一覧アイテム"""
    id: str
    name: str
    cooked_at: date
    category: Optional[CategoryResponse] = None
    thumbnail_url: Optional[str] = None
    image_count: int
    created_at: datetime


class DishListResponse(BaseModel):
    """料理一覧レスポンス"""
    items: List[DishListItemResponse]
    next_cursor: Optional[str] = None
    has_next: bool


class MessageResponse(BaseModel):
    """メッセージレスポンス"""
    message: str


# === Pre-signed URL関連 ===

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


class PresignedUrlRequest(BaseModel):
    """Pre-signed URL取得リクエスト"""
    content_type: str = Field(...)
    file_size: int = Field(..., ge=1, le=10485760)

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        if v not in ALLOWED_CONTENT_TYPES:
            raise ValueError(f"許可されていないMIMEタイプです: {v}")
        return v


class PresignedUrlResponse(BaseModel):
    """Pre-signed URLレスポンス"""
    upload_url: str
    image_key: str
    expires_in: int
