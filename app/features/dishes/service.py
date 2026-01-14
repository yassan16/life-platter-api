"""料理ビジネスロジック"""

from datetime import date
from typing import Optional, List

from sqlalchemy.orm import Session

from app.features.dishes.models import Dish, DishImage
from app.features.dishes.repository import (
    DishRepository,
    DishImageRepository,
    DishCategoryRepository,
)
from app.features.dishes.schemas import (
    DishCreateRequest,
    DishUpdateRequest,
    DishResponse,
    DishListResponse,
    DishListItemResponse,
    CategoryResponse,
    ImageResponse,
    MessageResponse,
)
from app.features.dishes.exceptions import (
    DishNotFoundError,
    PermissionDeniedError,
    ImageLimitExceededError,
    InvalidDisplayOrderError,
    CategoryNotFoundError,
    ImageNotFoundError,
    ImageNotOwnedError,
    S3ObjectNotFoundError,
)
from app.features.dishes.s3_service import s3_service


class DishService:
    """料理サービス"""

    MAX_IMAGES = 3

    def __init__(self, db: Session):
        self.db = db
        self.dish_repo = DishRepository(db)
        self.image_repo = DishImageRepository(db)
        self.category_repo = DishCategoryRepository(db)

    def create_dish(self, user_id: str, request: DishCreateRequest) -> DishResponse:
        """
        料理を登録
        1. バリデーション（画像数、display_order、カテゴリ）
        2. S3操作（画像存在確認、正式パスへコピー）
        3. DB保存
        4. 後処理（一時ファイル削除）
        """
        # バリデーション
        if request.images and len(request.images) > self.MAX_IMAGES:
            raise ImageLimitExceededError()

        if request.images:
            orders = [img.display_order for img in request.images]
            if len(orders) != len(set(orders)):
                raise InvalidDisplayOrderError()
            if any(o < 1 or o > 3 for o in orders):
                raise InvalidDisplayOrderError()

        if request.category_id:
            category = self.category_repo.find_by_id(request.category_id)
            if not category:
                raise CategoryNotFoundError()

        # S3操作（トランザクション外）
        temp_keys: List[str] = []
        if request.images:
            for img in request.images:
                # 存在確認
                if not s3_service.check_object_exists(img.image_key):
                    raise S3ObjectNotFoundError()
                temp_keys.append(img.image_key)

        # DB保存
        try:
            dish = self.dish_repo.create(
                user_id=user_id,
                name=request.name,
                cooked_at=request.cooked_at,
                category_id=request.category_id,
            )

            # 画像レコード作成
            if request.images:
                for img in request.images:
                    # 正式パスを生成
                    ext = img.image_key.split(".")[-1] if "." in img.image_key else "jpg"
                    permanent_key = s3_service.generate_permanent_key(
                        dish.id, img.display_order, ext
                    )

                    # S3コピー（スタブ）
                    s3_service.copy_to_permanent(img.image_key, permanent_key)

                    # DBレコード作成
                    self.image_repo.create(
                        dish_id=dish.id,
                        image_key=permanent_key,
                        display_order=img.display_order,
                    )

            self.dish_repo.commit()
            self.dish_repo.refresh(dish)

        except Exception:
            self.dish_repo.rollback()
            raise

        # 後処理（ベストエフォート）
        for key in temp_keys:
            s3_service.delete_object(key)

        return self._to_dish_response(dish)

    def get_dish(self, dish_id: str, user_id: str) -> DishResponse:
        """料理詳細を取得"""
        dish = self.dish_repo.find_by_id(dish_id)
        if not dish:
            raise DishNotFoundError()

        if dish.user_id != user_id:
            raise PermissionDeniedError()

        return self._to_dish_response(dish)

    def list_dishes(
        self,
        user_id: str,
        limit: int = 20,
        cursor: Optional[str] = None,
        category_id: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> DishListResponse:
        """料理一覧を取得"""
        results, has_next = self.dish_repo.find_list_with_pagination(
            user_id=user_id,
            limit=limit,
            cursor=cursor,
            category_id=category_id,
            from_date=from_date,
            to_date=to_date,
        )

        items = []
        for dish, thumbnail_key, image_count in results:
            thumbnail_url = None
            if thumbnail_key:
                thumbnail_url = s3_service.generate_image_url(thumbnail_key)

            category = None
            if dish.category:
                category = CategoryResponse(
                    id=dish.category.id,
                    name=dish.category.name,
                )

            items.append(
                DishListItemResponse(
                    id=dish.id,
                    name=dish.name,
                    cooked_at=dish.cooked_at,
                    category=category,
                    thumbnail_url=thumbnail_url,
                    image_count=image_count,
                    created_at=dish.created_at,
                )
            )

        # 次ページカーソル生成
        next_cursor = None
        if has_next and items:
            last_item = results[-1][0]  # 最後のDish
            next_cursor = self.dish_repo.encode_cursor(last_item.cooked_at, last_item.id)

        return DishListResponse(
            items=items,
            next_cursor=next_cursor,
            has_next=has_next,
        )

    def update_dish(
        self, dish_id: str, user_id: str, request: DishUpdateRequest
    ) -> DishResponse:
        """
        料理を更新（差分更新方式）
        1. 権限チェック
        2. バリデーション
        3. S3操作
        4. DB更新
        5. 後処理
        """
        dish = self.dish_repo.find_by_id(dish_id)
        if not dish:
            raise DishNotFoundError()

        if dish.user_id != user_id:
            raise PermissionDeniedError()

        # 画像数バリデーション
        current_count = len(dish.images)
        delete_count = len(request.images_to_delete) if request.images_to_delete else 0
        add_count = len(request.images_to_add) if request.images_to_add else 0
        final_count = current_count - delete_count + add_count

        if final_count > self.MAX_IMAGES:
            raise ImageLimitExceededError()

        # 削除対象画像のバリデーション
        images_to_delete: List[DishImage] = []
        if request.images_to_delete:
            current_image_ids = {img.id for img in dish.images}
            for image_id in request.images_to_delete:
                image = self.image_repo.find_by_id(image_id)
                if not image:
                    raise ImageNotFoundError()
                if image_id not in current_image_ids:
                    raise ImageNotOwnedError()
                images_to_delete.append(image)

        # カテゴリバリデーション
        if request.category_id:
            category = self.category_repo.find_by_id(request.category_id)
            if not category:
                raise CategoryNotFoundError()

        # S3操作（追加画像の存在確認）
        temp_keys: List[str] = []
        if request.images_to_add:
            for img in request.images_to_add:
                if not s3_service.check_object_exists(img.image_key):
                    raise S3ObjectNotFoundError()
                temp_keys.append(img.image_key)

        # DB更新
        try:
            # 基本情報更新
            self.dish_repo.update(
                dish=dish,
                name=request.name,
                cooked_at=request.cooked_at,
                category_id=request.category_id,
            )

            # 画像削除
            keys_to_delete_from_s3: List[str] = []
            if images_to_delete:
                for image in images_to_delete:
                    keys_to_delete_from_s3.append(image.image_key)
                self.image_repo.delete_by_ids(request.images_to_delete)

            # 画像追加
            if request.images_to_add:
                max_order = self.image_repo.get_max_display_order(dish_id)
                for i, img in enumerate(request.images_to_add):
                    new_order = max_order + i + 1
                    ext = img.image_key.split(".")[-1] if "." in img.image_key else "jpg"
                    permanent_key = s3_service.generate_permanent_key(
                        dish_id, new_order, ext
                    )

                    s3_service.copy_to_permanent(img.image_key, permanent_key)

                    self.image_repo.create(
                        dish_id=dish_id,
                        image_key=permanent_key,
                        display_order=new_order,
                    )

            self.dish_repo.commit()
            self.dish_repo.refresh(dish)

        except Exception:
            self.dish_repo.rollback()
            raise

        # 後処理（ベストエフォート）
        for key in temp_keys:
            s3_service.delete_object(key)
        for key in keys_to_delete_from_s3:
            s3_service.delete_object(key)

        return self._to_dish_response(dish)

    def delete_dish(self, dish_id: str, user_id: str) -> MessageResponse:
        """料理を論理削除"""
        dish = self.dish_repo.find_by_id(dish_id)
        if not dish:
            raise DishNotFoundError()

        if dish.user_id != user_id:
            raise PermissionDeniedError()

        self.dish_repo.soft_delete(dish)
        self.dish_repo.commit()

        return MessageResponse(message="料理を削除しました")

    def _to_dish_response(self, dish: Dish) -> DishResponse:
        """DishモデルをDishResponseに変換"""
        category = None
        if dish.category:
            category = CategoryResponse(
                id=dish.category.id,
                name=dish.category.name,
            )

        images = []
        for img in sorted(dish.images, key=lambda x: x.display_order):
            images.append(
                ImageResponse(
                    id=img.id,
                    image_url=s3_service.generate_image_url(img.image_key),
                    display_order=img.display_order,
                )
            )

        return DishResponse(
            id=dish.id,
            name=dish.name,
            cooked_at=dish.cooked_at,
            category=category,
            images=images,
            created_at=dish.created_at,
            updated_at=dish.updated_at,
        )
