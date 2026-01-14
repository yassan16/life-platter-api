# 料理画像アップロード仕様書

## 1. 概要

料理登録時の画像アップロードは **Pre-signed URL** 方式を採用する。

### Pre-signed URL方式とは

クライアントがAPIサーバー経由ではなく、S3に直接ファイルをアップロードする方式。
APIサーバーは署名付きURL（Pre-signed URL）を発行するのみ。

### 採用理由

| 観点 | Pre-signed URL | サーバー経由 |
|------|---------------|-------------|
| サーバー負荷 | 低（URLのみ発行） | 高（ファイル転送） |
| アップロード速度 | 高速（直接S3へ） | 低速（中継あり） |
| 大容量対応 | 最大5GB | サーバーメモリ制限 |
| スケーラビリティ | 高い | 低い |

---

## 2. アップロードフロー

### シーケンス図

```
┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐
│ Client │     │  API   │     │   S3   │     │   DB   │
└───┬────┘     └───┬────┘     └───┬────┘     └───┬────┘
    │              │              │              │
    │ 1. POST /dishes/images/presigned-url      │
    │──────────────>│              │              │
    │              │              │              │
    │   {upload_url, image_key}   │              │
    │<──────────────│              │              │
    │              │              │              │
    │ 2. PUT upload_url (画像バイナリ)           │
    │─────────────────────────────>│              │
    │              │              │              │
    │      200 OK  │              │              │
    │<─────────────────────────────│              │
    │              │              │              │
    │ 3. POST /dishes             │              │
    │   {name, images: [{image_key}]}            │
    │──────────────>│              │              │
    │              │ 4. S3画像存在確認           │
    │              │──────────────>│              │
    │              │      200 OK  │              │
    │              │<──────────────│              │
    │              │ 5. 正式パスにコピー          │
    │              │──────────────>│              │
    │              │              │              │
    │              │ 6. DBに保存  │              │
    │              │──────────────────────────────>│
    │              │              │              │
    │   201 Created│              │              │
    │<──────────────│              │              │
```

---

## 3. エンドポイント仕様

### POST /dishes/images/presigned-url

Pre-signed URLを取得するエンドポイント。

#### リクエスト

**ヘッダー**
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**ボディ**
```json
{
  "content_type": "image/jpeg",
  "file_size": 1048576
}
```

| フィールド | 型 | 必須 | 制約 | 説明 |
|-----------|------|:----:|------|------|
| content_type | string | Yes | image/jpeg, image/png, image/webp | MIMEタイプ |
| file_size | integer | Yes | 1〜10485760 (10MB) | ファイルサイズ（バイト） |

#### レスポンス

**成功: 200 OK**
```json
{
  "upload_url": "https://bucket.s3.ap-northeast-1.amazonaws.com/dishes/temp/...",
  "image_key": "dishes/temp/550e8400-e29b-41d4-a716-446655440000.jpg",
  "expires_in": 300
}
```

| フィールド | 型 | 説明 |
|-----------|------|------|
| upload_url | string | S3アップロード用署名付きURL |
| image_key | string | 料理登録時に使用するキー |
| expires_in | integer | URL有効期限（秒） |

#### エラーレスポンス

| HTTPステータス | error_code | 条件 |
|:-------------:|------------|------|
| 400 | `INVALID_CONTENT_TYPE` | 許可されていないMIMEタイプ |
| 400 | `FILE_SIZE_EXCEEDED` | ファイルサイズが上限超過 |
| 401 | `INVALID_TOKEN` | トークンが無効 |

---

## 4. セキュリティ要件

AWS公式ベストプラクティスに基づく設計。

### 4.1 Pre-signed URL設定

| 設定項目 | 値 | 理由 |
|---------|-----|------|
| 有効期限 | 5分（300秒） | 最小限の有効期間で漏洩リスク軽減 |
| HTTPメソッド | PUT のみ | アップロード専用、読み取り不可 |
| Content-Type | 指定必須 | 予期しないファイルタイプを防止 |
| Content-Length | 上限10MB | DoS攻撃防止 |

### 4.2 S3バケット設定

```
dishes/
├── temp/           # 一時アップロード領域（TTL: 24時間）
│   └── {uuid}.jpg
└── {dish_id}/      # 正式保存領域
    └── {order}.jpg
```

| 設定 | 値 | 説明 |
|------|-----|------|
| パブリックアクセス | 全てブロック | 直接アクセス禁止 |
| temp/ ライフサイクル | 24時間で自動削除 | 未使用ファイルの自動クリーンアップ |
| CORS | 許可オリジン指定 | フロントエンドドメインのみ許可 |
| 暗号化 | SSE-S3 | 保存時暗号化 |

### 4.3 IAMポリシー

#### アプリケーション用（最小権限）

Pre-signed URL生成と画像コピー/削除用:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PresignedUrlForTempUpload",
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::bucket-name/dishes/temp/*",
      "Condition": {
        "StringEquals": {
          "s3:x-amz-content-type": ["image/jpeg", "image/png", "image/webp"]
        }
      }
    },
    {
      "Sid": "CopyAndDeleteForDishImages",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::bucket-name/dishes/*"
    },
    {
      "Sid": "HeadObjectCheck",
      "Effect": "Allow",
      "Action": ["s3:HeadObject"],
      "Resource": "arn:aws:s3:::bucket-name/dishes/temp/*"
    }
  ]
}
```

#### 管理者用（コンソール/CLI操作）

AWS コンソールやCLIから画像を操作するための権限:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3AdminAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::bucket-name",
        "arn:aws:s3:::bucket-name/*"
      ]
    }
  ]
}
```

> **Note**: CloudFront OACはHTTP経由の外部アクセスを制御するもの。
> IAM認証を使用するコンソール/CLIからのアクセスは、上記IAMポリシーで制御される。

### 4.4 CORS設定

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["PUT"],
    "AllowedOrigins": ["https://your-domain.com"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

---

## 5. クライアント実装ガイド（Next.js）

### 5.1 画像アップロード関数

```typescript
interface PresignedUrlResponse {
  upload_url: string;
  image_key: string;
  expires_in: number;
}

async function uploadDishImage(file: File): Promise<string> {
  // 1. Pre-signed URLを取得
  const presignedRes = await fetch('/api/dishes/images/presigned-url', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      content_type: file.type,
      file_size: file.size,
    }),
  });

  if (!presignedRes.ok) {
    throw new Error('Failed to get presigned URL');
  }

  const { upload_url, image_key }: PresignedUrlResponse =
    await presignedRes.json();

  // 2. S3に直接アップロード
  const uploadRes = await fetch(upload_url, {
    method: 'PUT',
    body: file,
    headers: {
      'Content-Type': file.type,
    },
  });

  if (!uploadRes.ok) {
    throw new Error('Failed to upload to S3');
  }

  // 3. image_keyを返却（料理登録時に使用）
  return image_key;
}
```

### 5.2 料理登録フロー

```typescript
async function createDishWithImages(
  dishData: DishFormData,
  imageFiles: File[]
): Promise<Dish> {
  // 1. 全画像を並列アップロード
  const imageKeys = await Promise.all(
    imageFiles.map((file, index) =>
      uploadDishImage(file).then(key => ({
        image_key: key,
        display_order: index + 1,
      }))
    )
  );

  // 2. 料理を登録
  const response = await fetch('/api/dishes', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ...dishData,
      images: imageKeys,
    }),
  });

  return response.json();
}
```

---

## 6. エラーハンドリング

### クライアント側のリトライ戦略

| エラー | 対応 |
|--------|------|
| Pre-signed URL期限切れ | 新しいURLを取得してリトライ |
| S3アップロード失敗 | 最大3回リトライ（指数バックオフ） |
| ネットワークエラー | ユーザーに再試行を促す |

### サーバー側の整合性チェック

料理登録時:
1. `image_key` が `dishes/temp/` で始まることを検証
2. S3に該当オブジェクトが存在することを確認
3. Content-Typeがサポート形式であることを確認

---

## 7. 障害パターンとリカバリ

各処理ステップで障害が発生した場合の振る舞いと復旧方法を定義する。

### 7.1 障害パターン一覧

| # | 障害発生箇所 | 状態 | 自動リカバリ | 備考 |
|---|-------------|------|:------------:|------|
| 1 | Pre-signed URL発行 | DBなし、S3なし | - | クライアントでリトライ |
| 2 | S3アップロード | DBなし、S3なしor一部あり | ✅ | 一時ファイルは24h後に自動削除 |
| 3 | S3存在確認 | DBなし、S3一時領域あり | ✅ | 一時ファイルは24h後に自動削除 |
| 4 | S3コピー（正式パスへ） | DBなし、S3一時領域あり | ✅ | 一時ファイルは24h後に自動削除 |
| 5 | DBトランザクション | S3正式パスあり、DBなし | ✅ | 孤立ファイルは定期バッチで削除 |
| 6 | 一時ファイル削除 | DB完了、S3正式パスあり | ✅ | 24h後に自動削除 |
| 7 | 旧ファイル削除 | DB完了、S3正式パスあり | ⚠️ | 定期バッチで削除推奨 |

### 7.2 各パターンの詳細

#### パターン5: DBトランザクション失敗時

**状況**: S3コピーは成功したが、DBコミットが失敗

```
S3状態:
  dishes/temp/abc123.jpg     ← 一時ファイル（残留）
  dishes/{dish_id}/1.jpg     ← 正式パス（孤立ファイル）

DB状態:
  dishes: レコードなし
  dish_images: レコードなし
```

**リカバリ**:
- 一時ファイル: S3ライフサイクルルールで24時間後に自動削除
- 孤立ファイル: 定期バッチで`dish_images`に存在しないS3オブジェクトを削除

#### パターン7: 旧ファイル削除失敗時（更新処理）

**状況**: 料理更新完了後、旧画像の削除が失敗

```
S3状態:
  dishes/{dish_id}/1.jpg     ← 新画像（正常）
  dishes/{dish_id}/2.jpg     ← 旧画像（残留・ゴミ）

DB状態:
  dish_images: 新画像のみ参照
```

**リカバリ**:
- 定期バッチで`dish_images`に存在しないS3オブジェクトを削除

### 7.3 孤立ファイル削除バッチ（推奨実装）

`dish_images`テーブルに存在しない正式パスのS3オブジェクトを定期的に削除する。

```python
async def cleanup_orphan_images():
    """孤立した画像ファイルを削除するバッチ処理"""
    # 1. S3から正式パス配下のオブジェクト一覧を取得
    s3_objects = await list_s3_objects(prefix="dishes/")

    # 2. dish_imagesテーブルから全image_keyを取得
    db_image_keys = await get_all_image_keys()

    # 3. S3にあってDBにないオブジェクトを特定
    orphan_keys = [
        obj for obj in s3_objects
        if obj not in db_image_keys
        and not obj.startswith("dishes/temp/")  # 一時領域は除外
    ]

    # 4. 孤立ファイルを削除（作成から24時間以上経過したもののみ）
    for key in orphan_keys:
        if await is_older_than_24h(key):
            await delete_s3_object(key)
```

**実行頻度**: 1日1回（深夜帯推奨）

### 7.4 設計原則

1. **S3操作はトランザクション外で実行**: S3は2フェーズコミット非対応
2. **ゴミは許容、不整合は許容しない**: S3に不要ファイルが残ることは許容するが、DBが参照するファイルが存在しない状態は許容しない
3. **自動クリーンアップを前提とした設計**: ライフサイクルルールと定期バッチでゴミを回収

---

## 8. 一時ファイルのクリーンアップ

### 自動クリーンアップ（推奨）

S3ライフサイクルルールで `dishes/temp/` 配下を24時間後に自動削除。

```json
{
  "Rules": [
    {
      "ID": "DeleteTempImages",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "dishes/temp/"
      },
      "Expiration": {
        "Days": 1
      }
    }
  ]
}
```

### 料理登録成功後のクリーンアップ

料理登録が成功した後、バックグラウンドで一時ファイルを削除:

```python
# 非同期タスク（Celeryなど）
async def cleanup_temp_images(temp_keys: list[str]):
    for key in temp_keys:
        await s3_client.delete_object(Bucket=BUCKET, Key=key)
```

---

## 9. 画像配信（CloudFront）

### 9.1 アーキテクチャ

```
┌────────┐     ┌────────────┐     ┌────────┐
│ Client │────>│ CloudFront │────>│   S3   │
└────────┘     └────────────┘     └────────┘
                    │
              署名付きURL
              キャッシュ
```

### 9.2 CloudFront設定

| 設定項目 | 値 | 説明 |
|---------|-----|------|
| オリジン | S3バケット（OAC経由） | 直接S3アクセス禁止 |
| キャッシュポリシー | CachingOptimized | 画像に最適化 |
| TTL | 最小1日、最大365日 | 長期キャッシュ |
| ビューワープロトコル | HTTPS only | セキュリティ |
| 価格クラス | PriceClass_200 | 日本含むアジア最適化 |

### 9.3 Origin Access Control (OAC)

S3への直接アクセスを禁止し、CloudFront経由のみ許可。

**S3バケットポリシー:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudfront.amazonaws.com"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::bucket-name/dishes/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::account-id:distribution/distribution-id"
        }
      }
    }
  ]
}
```

### 9.4 署名付きURL生成（オプション）

プライベートコンテンツの場合、CloudFront署名付きURLを使用:

```python
from datetime import datetime, timedelta
from botocore.signers import CloudFrontSigner
import rsa

def generate_signed_url(image_key: str) -> str:
    """CloudFront署名付きURLを生成"""
    cloudfront_domain = "d1234567890.cloudfront.net"
    key_pair_id = "K1234567890"  # CloudFrontキーペアID

    url = f"https://{cloudfront_domain}/{image_key}"
    expire_date = datetime.utcnow() + timedelta(hours=1)

    # RSA署名
    def rsa_signer(message):
        with open('private_key.pem', 'rb') as f:
            private_key = rsa.PrivateKey.load_pkcs1(f.read())
        return rsa.sign(message, private_key, 'SHA-1')

    signer = CloudFrontSigner(key_pair_id, rsa_signer)
    signed_url = signer.generate_presigned_url(url, date_less_than=expire_date)

    return signed_url
```

### 9.5 レスポンスでの画像URL

料理取得APIのレスポンスでは、CloudFront URLを返却:

```json
{
  "images": [
    {
      "id": "...",
      "image_url": "https://d1234567890.cloudfront.net/dishes/550e8400/1.jpg",
      "display_order": 1
    }
  ]
}
```

---

## 10. 設定値一覧

| 設定項目 | 環境変数 | デフォルト値 |
|---------|---------|-------------|
| S3バケット名 | `S3_BUCKET_NAME` | （必須） |
| AWSリージョン | `AWS_REGION` | ap-northeast-1 |
| Pre-signed URL有効期限 | `PRESIGNED_URL_EXPIRES` | 300 |
| 最大ファイルサイズ | `MAX_IMAGE_SIZE` | 10485760 |
| 許可MIMEタイプ | - | image/jpeg, image/png, image/webp |
| CloudFrontドメイン | `CLOUDFRONT_DOMAIN` | （必須） |
| CloudFrontキーペアID | `CLOUDFRONT_KEY_PAIR_ID` | （署名付きURL使用時） |
| CloudFront秘密鍵パス | `CLOUDFRONT_PRIVATE_KEY_PATH` | （署名付きURL使用時） |

---

## 11. 実装ファイル構成

```
app/features/dishes/
├── s3_service.py       # S3操作（Pre-signed URL生成、コピー、削除）
├── router.py           # POST /dishes/images/presigned-url 追加
├── schemas.py          # PresignedUrlRequest, PresignedUrlResponse 追加
└── exceptions.py       # InvalidContentTypeError 追加
```

---

## 参考資料

- [AWS S3 Pre-signed URL Documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)
- [AWS Pre-signed URL Best Practices](https://docs.aws.amazon.com/pdfs/prescriptive-guidance/latest/presigned-url-best-practices/presigned-url-best-practices.pdf)
- [Securing Amazon S3 presigned URLs for serverless applications](https://aws.amazon.com/blogs/compute/securing-amazon-s3-presigned-urls-for-serverless-applications/)
