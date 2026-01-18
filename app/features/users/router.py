"""認証エンドポイント"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.features.users.models import User
from app.features.users.schemas import (
    RegisterRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
    MessageResponse,
)
from app.features.users.service import AuthService
from app.features.users.exceptions import (
    InvalidCredentialsError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserNotActiveError,
)


router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/users/register", response_model=TokenResponse, tags=["Users"])
@limiter.limit(settings.rate_limit_auth)
def register(
    request: Request,
    body: RegisterRequest,
    db: Session = Depends(get_db),
):
    """ユーザー登録"""
    try:
        service = AuthService(db)
        return service.register(body.username, body.email, body.password)
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "USER_ALREADY_EXISTS",
                "message": "このメールアドレスは既に登録されています",
                "details": None,
            },
        )


@router.post("/users/login", response_model=TokenResponse, tags=["Users"])
@limiter.limit(settings.rate_limit_auth)
def login(
    request: Request,
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    """ログイン"""
    try:
        service = AuthService(db)
        return service.login(body.email, body.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_CREDENTIALS",
                "message": "メールアドレスまたはパスワードが正しくありません",
                "details": None,
            },
        )
    except UserNotActiveError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "USER_NOT_ACTIVE",
                "message": "アカウントが無効です",
                "details": None,
            },
        )


@router.post("/users/refresh", response_model=TokenResponse, tags=["Users"])
@limiter.limit(settings.rate_limit_auth)
def refresh(
    request: Request,
    body: RefreshRequest,
    db: Session = Depends(get_db),
):
    """トークン更新"""
    try:
        service = AuthService(db)
        return service.refresh(body.refresh_token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_TOKEN",
                "message": "トークンが無効または期限切れです",
                "details": None,
            },
        )
    except UserNotActiveError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "USER_NOT_ACTIVE",
                "message": "アカウントが無効です",
                "details": None,
            },
        )


@router.post("/users/logout", response_model=MessageResponse, tags=["Users"])
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ログアウト"""
    service = AuthService(db)
    service.logout(current_user)
    return MessageResponse(message="ログアウトしました")


@router.get("/users/me", response_model=UserResponse, tags=["Users"])
def get_me(current_user: User = Depends(get_current_user)):
    """現在のユーザー情報"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        status=current_user.status.value,
    )
