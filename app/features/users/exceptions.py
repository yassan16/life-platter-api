"""認証関連のカスタム例外"""


class InvalidCredentialsError(Exception):
    """認証情報が無効（ログイン失敗）"""
    pass


class InvalidTokenError(Exception):
    """トークンが無効または期限切れ"""
    pass


class UserAlreadyExistsError(Exception):
    """ユーザーが既に存在する（メールアドレス重複）"""
    pass


class UserNotActiveError(Exception):
    """ユーザーがアクティブでない"""
    pass
