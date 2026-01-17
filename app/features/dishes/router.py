"""料理エンドポイント"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.features.users.models import User
from app.features.dishes.schemas import (
    DishCreateRequest,
    DishUpdateRequest,
    DishResponse,
    DishListResponse,
    MessageResponse,
    PresignedUrlRequest,
    PresignedUrlResponse,
)
from app.features.dishes.service import DishService
from app.features.dishes.s3_service import s3_service
from app.features.dishes.exceptions import (
    DishNotFoundError,
    PermissionDeniedError,
    ImageLimitExceededError,
    InvalidDisplayOrderError,
    InvalidCursorError,
    CategoryNotFoundError,
    ImageNotFoundError,
    ImageNotOwnedError,
    S3ObjectNotFoundError,
)


router = APIRouter(prefix="/dishes", tags=["Dishes"])


@router.post("", response_model=DishResponse, status_code=status.HTTP_201_CREATED)
def create_dish(
    request: DishCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """料理を登録"""
    try:
        service = DishService(db)
        return service.create_dish(current_user.id, request)
    except ImageLimitExceededError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "IMAGE_LIMIT_EXCEEDED",
                "message": "画像は最大3枚まで登録できます",
                "details": None,
            },
        )
    except InvalidDisplayOrderError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_DISPLAY_ORDER",
                "message": "display_orderが不正です（重複または範囲外）",
                "details": None,
            },
        )
    except CategoryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "CATEGORY_NOT_FOUND",
                "message": "指定されたカテゴリが存在しません",
                "details": None,
            },
        )
    except S3ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "S3_OBJECT_NOT_FOUND",
                "message": "指定された画像ファイルが存在しません",
                "details": None,
            },
        )


@router.get("", response_model=DishListResponse)
def list_dishes(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    category_id: Optional[str] = Query(default=None),
    from_date: Optional[date] = Query(default=None),
    to_date: Optional[date] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """料理一覧を取得"""
    try:
        service = DishService(db)
        return service.list_dishes(
            user_id=current_user.id,
            limit=limit,
            cursor=cursor,
            category_id=category_id,
            from_date=from_date,
            to_date=to_date,
        )
    except InvalidCursorError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_CURSOR",
                "message": "カーソルが不正です",
                "details": None,
            },
        )


@router.post(
    "/images/presigned-url",
    response_model=PresignedUrlResponse,
    status_code=status.HTTP_200_OK,
)
def get_presigned_url(
    request: PresignedUrlRequest,
    current_user: User = Depends(get_current_user),
):
    """画像アップロード用のPre-signed URLを取得"""
    result = s3_service.generate_presigned_url(
        content_type=request.content_type,
        file_size=request.file_size,
    )
    return PresignedUrlResponse(**result)


@router.get("/{dish_id}", response_model=DishResponse)
def get_dish(
    dish_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """料理詳細を取得"""
    try:
        service = DishService(db)
        return service.get_dish(dish_id, current_user.id)
    except DishNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "DISH_NOT_FOUND",
                "message": "指定された料理が存在しません",
                "details": None,
            },
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "PERMISSION_DENIED",
                "message": "この料理にアクセスする権限がありません",
                "details": None,
            },
        )


@router.put("/{dish_id}", response_model=DishResponse)
def update_dish(
    dish_id: str,
    request: DishUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """料理を更新"""
    try:
        service = DishService(db)
        return service.update_dish(dish_id, current_user.id, request)
    except DishNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "DISH_NOT_FOUND",
                "message": "指定された料理が存在しません",
                "details": None,
            },
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "PERMISSION_DENIED",
                "message": "この料理を更新する権限がありません",
                "details": None,
            },
        )
    except ImageLimitExceededError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "IMAGE_LIMIT_EXCEEDED",
                "message": "画像は最大3枚まで登録できます",
                "details": None,
            },
        )
    except ImageNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "IMAGE_NOT_FOUND",
                "message": "削除対象の画像が存在しません",
                "details": None,
            },
        )
    except ImageNotOwnedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "IMAGE_NOT_OWNED",
                "message": "削除対象の画像がこの料理に属していません",
                "details": None,
            },
        )
    except CategoryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "CATEGORY_NOT_FOUND",
                "message": "指定されたカテゴリが存在しません",
                "details": None,
            },
        )
    except S3ObjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "S3_OBJECT_NOT_FOUND",
                "message": "指定された画像ファイルが存在しません",
                "details": None,
            },
        )


@router.delete("/{dish_id}", response_model=MessageResponse)
def delete_dish(
    dish_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """料理を削除（論理削除）"""
    try:
        service = DishService(db)
        return service.delete_dish(dish_id, current_user.id)
    except DishNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "DISH_NOT_FOUND",
                "message": "指定された料理が存在しません",
                "details": None,
            },
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "PERMISSION_DENIED",
                "message": "この料理を削除する権限がありません",
                "details": None,
            },
        )
