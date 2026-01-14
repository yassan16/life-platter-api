"""料理機能のカスタム例外"""


class DishNotFoundError(Exception):
    """料理が存在しないまたは削除済み"""
    pass


class PermissionDeniedError(Exception):
    """他ユーザーの料理へのアクセス"""
    pass


class ImageLimitExceededError(Exception):
    """画像枚数が上限超過（最大3枚）"""
    pass


class InvalidDisplayOrderError(Exception):
    """display_orderが不正（重複または範囲外）"""
    pass


class InvalidCursorError(Exception):
    """ページネーションカーソルが不正"""
    pass


class CategoryNotFoundError(Exception):
    """カテゴリが存在しない"""
    pass


class ImageNotFoundError(Exception):
    """画像が存在しない"""
    pass


class ImageNotOwnedError(Exception):
    """画像が該当料理に属していない"""
    pass


class S3ObjectNotFoundError(Exception):
    """S3オブジェクトが存在しない"""
    pass
