"""統合APIルーター"""

from fastapi import APIRouter

from app.features.users.router import router as users_router
from app.features.dishes.router import router as dishes_router

api_router = APIRouter()
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(dishes_router, prefix="/dishes", tags=["Dishes"])
