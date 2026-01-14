"""料理DB操作リポジトリ"""

import base64
import json
from datetime import date, datetime, timezone
from typing import Optional, List, Tuple

from sqlalchemy import func, select, and_, or_
from sqlalchemy.orm import Session, joinedload

from app.features.dishes.models import Dish, DishImage, DishCategory
from app.features.dishes.exceptions import InvalidCursorError


class DishRepository:
    """料理リポジトリ"""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: str,
        name: str,
        cooked_at: date,
        category_id: Optional[str] = None,
    ) -> Dish:
        """料理を作成"""
        dish = Dish(
            user_id=user_id,
            name=name,
            cooked_at=cooked_at,
            category_id=category_id,
        )
        self.db.add(dish)
        self.db.flush()
        return dish

    def find_by_id(self, dish_id: str) -> Optional[Dish]:
        """IDで料理を取得（論理削除除外、リレーション含む）"""
        return (
            self.db.query(Dish)
            .options(
                joinedload(Dish.category),
                joinedload(Dish.images),
            )
            .filter(
                Dish.id == dish_id,
                Dish.deleted_at.is_(None),
            )
            .first()
        )

    def find_by_id_for_user(self, dish_id: str, user_id: str) -> Optional[Dish]:
        """IDとユーザーIDで料理を取得"""
        return (
            self.db.query(Dish)
            .options(
                joinedload(Dish.category),
                joinedload(Dish.images),
            )
            .filter(
                Dish.id == dish_id,
                Dish.user_id == user_id,
                Dish.deleted_at.is_(None),
            )
            .first()
        )

    def find_list_with_pagination(
        self,
        user_id: str,
        limit: int = 20,
        cursor: Optional[str] = None,
        category_id: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> Tuple[List[Tuple[Dish, Optional[str], int]], bool]:
        """
        ページネーション付きで料理一覧を取得

        Returns:
            Tuple of (items, has_next)
            items: List of (Dish, thumbnail_key, image_count)
        """
        # サブクエリ: display_order=1 の image_key を取得
        thumbnail_subquery = (
            select(DishImage.image_key)
            .where(
                and_(
                    DishImage.dish_id == Dish.id,
                    DishImage.display_order == 1,
                )
            )
            .correlate(Dish)
            .scalar_subquery()
        )

        # サブクエリ: 画像の件数を取得
        count_subquery = (
            select(func.count(DishImage.id))
            .where(DishImage.dish_id == Dish.id)
            .correlate(Dish)
            .scalar_subquery()
        )

        # ベースクエリ
        query = (
            self.db.query(
                Dish,
                thumbnail_subquery.label("thumbnail_key"),
                count_subquery.label("image_count"),
            )
            .options(joinedload(Dish.category))
            .filter(Dish.user_id == user_id)
            .filter(Dish.deleted_at.is_(None))
        )

        # カテゴリフィルタ
        if category_id:
            query = query.filter(Dish.category_id == category_id)

        # 日付範囲フィルタ
        if from_date:
            query = query.filter(Dish.cooked_at >= from_date)
        if to_date:
            query = query.filter(Dish.cooked_at <= to_date)

        # カーソル条件
        if cursor:
            cursor_cooked_at, cursor_id = self._decode_cursor(cursor)
            query = query.filter(
                or_(
                    Dish.cooked_at < cursor_cooked_at,
                    and_(
                        Dish.cooked_at == cursor_cooked_at,
                        Dish.id < cursor_id,
                    ),
                )
            )

        # ソートと取得
        query = query.order_by(Dish.cooked_at.desc(), Dish.id.desc())
        results = query.limit(limit + 1).all()

        # 次ページ判定
        has_next = len(results) > limit
        if has_next:
            results = results[:limit]

        return results, has_next

    def update(
        self,
        dish: Dish,
        name: str,
        cooked_at: date,
        category_id: Optional[str] = None,
    ) -> Dish:
        """料理を更新"""
        dish.name = name
        dish.cooked_at = cooked_at
        dish.category_id = category_id
        self.db.flush()
        return dish

    def soft_delete(self, dish: Dish) -> None:
        """料理を論理削除"""
        dish.deleted_at = datetime.now(timezone.utc)
        self.db.flush()

    def commit(self) -> None:
        """トランザクションをコミット"""
        self.db.commit()

    def rollback(self) -> None:
        """トランザクションをロールバック"""
        self.db.rollback()

    def refresh(self, obj) -> None:
        """オブジェクトをリフレッシュ"""
        self.db.refresh(obj)

    @staticmethod
    def encode_cursor(cooked_at: date, dish_id: str) -> str:
        """カーソルをBase64エンコード"""
        data = {"cooked_at": cooked_at.isoformat(), "id": dish_id}
        json_str = json.dumps(data)
        return base64.urlsafe_b64encode(json_str.encode()).decode()

    @staticmethod
    def _decode_cursor(cursor: str) -> Tuple[date, str]:
        """カーソルをデコード"""
        try:
            json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
            data = json.loads(json_str)
            return date.fromisoformat(data["cooked_at"]), data["id"]
        except Exception:
            raise InvalidCursorError()


class DishImageRepository:
    """料理画像リポジトリ"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, dish_id: str, image_key: str, display_order: int) -> DishImage:
        """画像レコードを作成"""
        image = DishImage(
            dish_id=dish_id,
            image_key=image_key,
            display_order=display_order,
        )
        self.db.add(image)
        self.db.flush()
        return image

    def find_by_id(self, image_id: str) -> Optional[DishImage]:
        """IDで画像を取得"""
        return self.db.query(DishImage).filter(DishImage.id == image_id).first()

    def find_by_dish_id(self, dish_id: str) -> List[DishImage]:
        """料理IDで画像一覧を取得"""
        return (
            self.db.query(DishImage)
            .filter(DishImage.dish_id == dish_id)
            .order_by(DishImage.display_order)
            .all()
        )

    def get_max_display_order(self, dish_id: str) -> int:
        """料理の最大display_orderを取得"""
        result = (
            self.db.query(func.max(DishImage.display_order))
            .filter(DishImage.dish_id == dish_id)
            .scalar()
        )
        return result or 0

    def delete(self, image: DishImage) -> None:
        """画像レコードを物理削除"""
        self.db.delete(image)
        self.db.flush()

    def delete_by_ids(self, image_ids: List[str]) -> None:
        """複数の画像レコードを物理削除"""
        self.db.query(DishImage).filter(DishImage.id.in_(image_ids)).delete(
            synchronize_session=False
        )
        self.db.flush()


class DishCategoryRepository:
    """料理カテゴリリポジトリ"""

    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, category_id: str) -> Optional[DishCategory]:
        """IDでカテゴリを取得（論理削除除外）"""
        return (
            self.db.query(DishCategory)
            .filter(
                DishCategory.id == category_id,
                DishCategory.deleted_at.is_(None),
            )
            .first()
        )
