"""
全モデルをここでインポート
Alembicの autogenerate がモデルを検出するために必要
"""

from app.features.users.models import User, RefreshToken
from app.features.dishes.models import DishCategory, Dish, DishImage

# 新しいモデルを追加したら、ここにもインポートを追加する
# from app.features.ingredients.models import Ingredient
