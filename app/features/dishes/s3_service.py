"""S3操作サービス

NOTE: S3_BUCKET_NAMEが未設定の場合はスタブモードで動作します。
"""

import os
import uuid

import boto3
from botocore.config import Config

from app.core.config import S3_BUCKET_NAME, AWS_REGION, PRESIGNED_URL_EXPIRES


# 設定値
CLOUDFRONT_DOMAIN = os.getenv("CLOUDFRONT_DOMAIN", "https://d1234567890.cloudfront.net")

CONTENT_TYPE_TO_EXTENSION = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class S3Service:
    """S3操作サービス"""

    def __init__(self):
        self.bucket_name = S3_BUCKET_NAME
        self.region = AWS_REGION
        self.presigned_url_expires = PRESIGNED_URL_EXPIRES

        if self.bucket_name:
            self.s3_client = boto3.client(
                "s3",
                region_name=self.region,
                config=Config(signature_version="s3v4"),
            )
        else:
            self.s3_client = None  # スタブモード

    def generate_presigned_url(self, content_type: str, file_size: int) -> dict:
        """Pre-signed URLを生成

        Args:
            content_type: MIMEタイプ
            file_size: ファイルサイズ（バイト）

        Returns:
            upload_url, image_key, expires_in を含む辞書
        """
        extension = CONTENT_TYPE_TO_EXTENSION.get(content_type, "jpg")
        image_key = f"dishes/temp/{uuid.uuid4()}.{extension}"

        if self.s3_client is None:
            # スタブモード（S3_BUCKET_NAMEが未設定の場合）
            return {
                "upload_url": f"https://stub-bucket.s3.{self.region}.amazonaws.com/{image_key}?stub=true",
                "image_key": image_key,
                "expires_in": self.presigned_url_expires,
            }

        upload_url = self.s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": image_key,
                "ContentType": content_type,
                "ContentLength": file_size,
            },
            ExpiresIn=self.presigned_url_expires,
        )
        return {
            "upload_url": upload_url,
            "image_key": image_key,
            "expires_in": self.presigned_url_expires,
        }

    def check_object_exists(self, image_key: str) -> bool:
        """
        S3オブジェクトの存在確認

        Args:
            image_key: S3オブジェクトキー（例: dishes/temp/abc123.jpg）

        Returns:
            bool: オブジェクトが存在する場合True
        """
        if self.s3_client is None:
            # スタブモード: 常にTrueを返す
            return True
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
        """
        if self.s3_client is None:
            # スタブモード: 常にTrueを返す
            return True
        # TODO: s3_client.copy_object(...)
        return True

    def delete_object(self, image_key: str) -> bool:
        """
        S3オブジェクトを削除（ベストエフォート）

        Args:
            image_key: 削除対象のキー

        Returns:
            bool: 削除成功の場合True（失敗しても問題なし）
        """
        if self.s3_client is None:
            # スタブモード: 常にTrueを返す
            return True
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
