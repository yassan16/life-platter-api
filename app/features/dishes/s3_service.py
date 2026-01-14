"""S3操作サービス（スタブ実装）

NOTE: このファイルはS3操作のインターフェースを定義しています。
現在はスタブ実装となっており、実際のS3操作は行いません。
将来のS3統合時に実装を置き換えてください。
"""

import os


# 設定値
CLOUDFRONT_DOMAIN = os.getenv("CLOUDFRONT_DOMAIN", "https://d1234567890.cloudfront.net")


class S3Service:
    """S3操作サービス（スタブ）"""

    def __init__(self):
        # TODO: S3クライアント初期化
        # self.s3_client = boto3.client('s3')
        # self.bucket_name = os.getenv("S3_BUCKET_NAME")
        pass

    def check_object_exists(self, image_key: str) -> bool:
        """
        S3オブジェクトの存在確認

        Args:
            image_key: S3オブジェクトキー（例: dishes/temp/abc123.jpg）

        Returns:
            bool: オブジェクトが存在する場合True

        TODO: 実際のS3 HeadObject呼び出しに置き換え
        """
        # スタブ: 常にTrueを返す
        # TODO: boto3.client('s3').head_object(Bucket=bucket, Key=image_key)
        return True

    def copy_to_permanent(self, temp_key: str, permanent_key: str) -> bool:
        """
        一時ファイルを正式パスにコピー

        Args:
            temp_key: 一時領域のキー（例: dishes/temp/abc123.jpg）
            permanent_key: 正式パス（例: dishes/{dish_id}/1.jpg）

        Returns:
            bool: コピー成功の場合True

        TODO: 実際のS3 CopyObject呼び出しに置き換え
        """
        # スタブ: 常にTrueを返す
        # TODO: s3_client.copy_object(...)
        return True

    def delete_object(self, image_key: str) -> bool:
        """
        S3オブジェクトを削除（ベストエフォート）

        Args:
            image_key: 削除対象のキー

        Returns:
            bool: 削除成功の場合True（失敗しても問題なし）

        TODO: 実際のS3 DeleteObject呼び出しに置き換え
        """
        # スタブ: 常にTrueを返す
        # TODO: s3_client.delete_object(Bucket=bucket, Key=image_key)
        return True

    def generate_image_url(self, image_key: str) -> str:
        """
        画像のCloudFront URLを生成

        Args:
            image_key: S3オブジェクトキー

        Returns:
            str: CloudFront経由の画像URL
        """
        return f"{CLOUDFRONT_DOMAIN}/{image_key}"

    def generate_permanent_key(
        self, dish_id: str, display_order: int, extension: str = "jpg"
    ) -> str:
        """
        正式パスのキーを生成

        Args:
            dish_id: 料理ID
            display_order: 表示順序
            extension: ファイル拡張子

        Returns:
            str: 正式パスのキー（例: dishes/{dish_id}/1.jpg）
        """
        return f"dishes/{dish_id}/{display_order}.{extension}"


# シングルトンインスタンス
s3_service = S3Service()
