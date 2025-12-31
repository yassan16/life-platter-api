"""Pydantic スキーマ"""

from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field


# === リクエストスキーマ ===

class RegisterRequest(BaseModel):
    """ユーザー登録リクエスト"""
    username: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)


class LoginRequest(BaseModel):
    """ログインリクエスト"""
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """トークン更新リクエスト"""
    refresh_token: str


# === レスポンススキーマ ===

class TokenResponse(BaseModel):
    """トークンレスポンス"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """ユーザー情報レスポンス"""
    id: str
    username: str
    email: str
    status: str

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """メッセージレスポンス"""
    message: str


# === エラースキーマ ===

class ErrorDetail(BaseModel):
    """エラー詳細"""
    field: str
    reason: str


class ErrorResponse(BaseModel):
    """エラーレスポンス（統一形式）"""
    error_code: str
    message: str
    details: Optional[List[ErrorDetail]] = None
