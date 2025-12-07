from fastapi import APIRouter

# ルーターの定義
router = APIRouter()

# GET /cooking/
@router.get("/")
def get_cookings():
    # 本来はDBから取得しますが、まずはダミーデータで動作確認
    return [
        {"id": 1, "name": "カレーライス", "category": "洋食"},
        {"id": 2, "name": "肉じゃが", "category": "和食"}
    ]
