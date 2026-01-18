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

### なぜクライアントからS3に直接アップロードできるのか

S3バケットはパブリックアクセスをブロックしており、通常はAWS認証情報がないとアクセスできない。
しかし、認証情報をクライアントに渡すのはセキュリティ上危険である。

Pre-signed URLは、この問題を**一時的な署名をURLに埋め込む**ことで解決する。

```
署名付きURL = S3のURL + 一時的な認証情報（署名）

https://bucket.s3.amazonaws.com/dishes/temp/xxx.jpg
  ?X-Amz-Algorithm=AWS4-HMAC-SHA256
  &X-Amz-Credential=AKIA.../s3/aws4_request
  &X-Amz-Date=20240114T...
  &X-Amz-Expires=300          ← 5分間だけ有効
  &X-Amz-Signature=abc123...  ← サーバーが生成した署名
```

**処理の流れ:**

1. クライアントがAPIサーバーに「アップロードしたい」とリクエスト
2. APIサーバーがAWS認証情報を使って署名を生成し、署名付きURLを返却
3. クライアントが署名付きURLに対してPUTリクエスト（画像バイナリを送信）
4. S3が署名を検証し、有効であればファイルを保存

```
通信経路の比較:

サーバー経由方式:
  クライアント → APIサーバー → S3
  [   通信1   ] + [   通信2   ]  ← 2回転送

Pre-signed URL方式:
  クライアント → API（URLのみ）     ← 数KB、一瞬
  クライアント → S3（画像）         ← 1回転送のみ
```

**S3側の検証処理:**

1. URLの`X-Amz-Signature`を取り出す
2. リクエスト内容（パス、メソッド、日時等）から署名を再計算
3. 署名が一致するか確認
4. 有効期限内か確認
5. すべてOKならファイルを保存して200 OKを返却

**セキュリティが担保される理由:**

| 制約 | 値 | 効果 |
|------|-----|------|
| 有効期限 | 5分 | URL漏洩しても短時間で無効化 |
| HTTPメソッド | PUTのみ | 読み取り・削除は不可 |
| Content-Type | 指定必須 | 画像以外アップロード不可 |
| パス | `dishes/temp/*`のみ | 他のパスには書き込み不可 |

---

## 2. なぜ一時ファイル（temp）が必要なのか？

### 2.1 問題提起：S3とDBの操作タイミングのズレ

料理画像のアップロードでは、以下のジレンマが存在する。

**理想の画像パス構造:**
```
dishes/{dish_id}/{display_order}.jpg
例: dishes/12345/1.jpg
```

**問題:**
- クライアントがS3に直接アップロードする時点では、まだ料理が登録されていない
- DB INSERTが完了して初めて`dish_id`が確定する
- しかし、S3アップロードはDB登録の前に実行される必要がある

**タイムライン:**
```
❌ 不可能なフロー:
  1. dish_idを取得する        ← まだ料理が存在しない！
  2. S3にアップロード: dishes/{dish_id}/1.jpg
  3. 料理をDBに登録
```

### 2.2 なぜdish_idが事前に確定できないのか

| 理由 | 詳細 |
|------|------|
| クライアント直接アップロード方式 | Pre-signed URL方式では、クライアントが直接S3にアップロードするため、APIサーバーはアップロード時点で料理情報を持たない |
| DB INSERTのタイミング | dish_idはDBのAUTO_INCREMENTで生成されるため、INSERTが完了するまで確定しない |
| トランザクション整合性 | 画像アップロード後に料理登録が失敗する可能性があり、dish_idを先に予約すると欠番が発生する |

### 2.3 解決策：2段階パス方式

一時パスを経由することで、この問題を解決する。

**フロー:**
```
✅ 実際のフロー:
  1. S3にアップロード: dishes/temp/{uuid}.jpg    ← 一時保存
  2. 料理をDBに登録 → dish_idが確定
  3. S3内でコピー: dishes/temp/{uuid}.jpg → dishes/{dish_id}/1.jpg
  4. 一時ファイルを削除（オプション）
```

**メリット:**
| 項目 | 説明 |
|------|------|
| dish_id不要 | アップロード時点でdish_idが不要 |
| 整合性確保 | 料理登録が失敗しても、一時ファイルは24時間後に自動削除される |
| パス一貫性 | 最終的には理想のパス構造 `dishes/{dish_id}/` を維持 |

### 2.4 詳細フロー図

各ステップでのS3とDBの状態を明示。

```
ステップ1: 画像アップロード
┌────────────────────────────────┐
│ S3: dishes/temp/abc-123.jpg    │ ← 一時保存
│ DB: （料理未登録）              │
└────────────────────────────────┘

ステップ2: 料理登録
┌────────────────────────────────┐
│ S3: dishes/temp/abc-123.jpg    │
│ DB: INSERT INTO dishes         │
│     → dish_id = 550 確定       │ ← dish_idが生成される
└────────────────────────────────┘

ステップ3: 正式パスにコピー
┌────────────────────────────────┐
│ S3: dishes/temp/abc-123.jpg    │ ← 元ファイル残存
│     dishes/550/1.jpg           │ ← コピー完了
│ DB: dish_id=550, image_key=... │
└────────────────────────────────┘

ステップ4: 一時ファイル削除（24時間後に自動 or 即座に削除）
┌────────────────────────────────┐
│ S3: dishes/550/1.jpg           │ ← 正式パスのみ残る
│ DB: dish_id=550, image_key=... │
└────────────────────────────────┘
```

---

## 3. アップロードフロー

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

## 4. 未実装機能の必要性

現在のシーケンス図（`## 3. アップロードフロー`）では、以下の3つの未実装機能が存在する。

```
4. S3画像存在確認          → check_object_exists()
5. 正式パスにコピー        → copy_to_permanent()
一時ファイル削除           → delete_object()
```

これらの機能が**なぜ必要なのか**を、技術的背景とともに解説する。

### 4.1 check_object_exists() - S3オブジェクト存在確認

**目的:** セキュリティと整合性の確保

**なぜ必要？**

| シナリオ | 存在確認なし | 存在確認あり |
|---------|-------------|-------------|
| アップロード失敗 | DB登録が成功してしまい、画像URLが404になる（不整合） | 事前検知してエラー返却、DB登録を中止 |
| 悪意のあるユーザー | 存在しない`image_key`を送信してDBに不正データを保存 | 不正リクエストを検知して拒否 |
| ネットワークエラー | S3アップロード途中でタイムアウトしたが気づかない | 早期検出してユーザーに再試行を促せる |

**実装方法:**

```python
import boto3
from botocore.exceptions import ClientError

async def check_object_exists(bucket: str, key: str) -> bool:
    """S3オブジェクトの存在確認

    Args:
        bucket: S3バケット名
        key: オブジェクトキー（例: dishes/temp/abc-123.jpg）

    Returns:
        True: オブジェクトが存在する
        False: オブジェクトが存在しない
    """
    s3_client = boto3.client('s3')

    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        else:
            # その他のエラー（権限エラーなど）
            raise
```

**EC2→S3アクセス:** ✅ あり（HeadObjectリクエスト、軽量）

**使用箇所:** 料理登録API（POST /dishes）の入力検証

---

### 4.2 copy_to_permanent() - 正式パスへのコピー

**目的:** dish_id確定後の正式保存

**なぜ必要？**

1. **dish_idはDB登録後にしか確定しない**
   - AUTO_INCREMENTでIDが生成されるため、INSERT完了まで不明
   - クライアントアップロード時点ではdish_idを含むパスを使えない

2. **画像パスの一貫性**
   - すべての画像を`dishes/{dish_id}/`配下に統一
   - CloudFront URL生成やバッチ処理がシンプルになる

3. **temp領域の自動クリーンアップとの連携**
   - tempファイルは24時間後に自動削除される
   - コピーせずに放置すると、画像が消失する

**実装方法:**

```python
import boto3

async def copy_to_permanent(
    bucket: str,
    source_key: str,
    destination_key: str
) -> None:
    """S3内でオブジェクトをコピー（サーバーサイドコピー）

    Args:
        bucket: S3バケット名
        source_key: コピー元キー（例: dishes/temp/abc-123.jpg）
        destination_key: コピー先キー（例: dishes/550/1.jpg）
    """
    s3_client = boto3.client('s3')

    copy_source = {'Bucket': bucket, 'Key': source_key}

    s3_client.copy_object(
        CopySource=copy_source,
        Bucket=bucket,
        Key=destination_key,
        MetadataDirective='COPY',  # メタデータもコピー
        ServerSideEncryption='AES256'  # 暗号化
    )
```

**EC2→S3アクセス:** ✅ あり（CopyObjectリクエスト）
- **注意:** S3内コピーなので、ファイルはEC2を経由せずS3内で直接コピーされる（高速）

**使用箇所:** 料理登録API（POST /dishes）のDB保存直前

---

### 4.3 delete_object() - オブジェクト削除

**目的:** 不要ファイルの削除

**なぜ必要？**

| ケース | 削除対象 | 重要度 | 理由 |
|--------|---------|:------:|------|
| 料理登録完了後 | tempファイル | 低 | 24h後に自動削除されるため必須ではない |
| 料理更新時 | 古い画像 | 高 | 自動削除されず、放置するとゴミが蓄積 |
| 料理削除時 | 全画像 | 高 | 孤立ファイルとしてストレージコストが発生 |

**設計原則:**

> **ゴミは許容、不整合は許容しない**
>
> - S3に不要ファイルが残ることは許容する（定期バッチで削除）
> - DBが参照する画像が存在しない状態は絶対に許容しない（ユーザーに404エラー）

**実装方法:**

```python
import boto3

async def delete_object(bucket: str, key: str) -> None:
    """S3オブジェクトを削除

    Args:
        bucket: S3バケット名
        key: 削除するオブジェクトキー
    """
    s3_client = boto3.client('s3')

    try:
        s3_client.delete_object(Bucket=bucket, Key=key)
    except Exception as e:
        # 削除失敗はログ記録のみ、エラーを投げない
        # → ゴミファイルは許容する設計
        logger.warning(f"Failed to delete S3 object: {key}, error: {e}")
```

**EC2→S3アクセス:** ✅ あり（DeleteObjectリクエスト）

**使用箇所:**
- 料理登録完了後（バックグラウンドタスク）
- 料理更新API（PUT /dishes/{id}）
- 料理削除API（DELETE /dishes/{id}）

---

## 5. EC2からS3へのアクセスパターン

各操作におけるEC2とS3間の通信を整理。

| 操作 | 実装状況 | EC2→S3 | タイミング | S3 API | 説明 |
|------|---------|:------:|----------|--------|------|
| Pre-signed URL生成 | ✅ 実装済み | あり | Pre-signed URL取得時 | - | boto3でs3:PutObjectの署名生成（S3リクエストなし） |
| 画像存在確認 | ❌ TODO | あり（将来） | 料理登録時 | HeadObject | S3オブジェクトのメタデータ取得 |
| 正式パスにコピー | ❌ TODO | あり（将来） | 料理登録時 | CopyObject | S3内コピー（EC2経由なし、高速） |
| 一時ファイル削除 | ❌ TODO | あり（将来） | 料理登録後 | DeleteObject | S3オブジェクト削除 |
| CloudFront URL生成 | ✅ 実装済み | なし | 画像URL生成時 | - | 文字列組み立てのみ（`https://{domain}/{key}`） |

**注意事項:**

1. **Pre-signed URL生成はS3リクエストを発行しない**
   - 署名生成はローカル処理（AWS認証情報を使って暗号化するだけ）
   - S3への通信は発生しない

2. **CopyObjectはEC2のメモリを使わない**
   - S3内で直接コピーされるため、大容量ファイルでもEC2負荷なし
   - 数GB規模でも高速処理可能

3. **HeadObjectは軽量**
   - ファイル本体を取得せず、メタデータのみ（数百バイト）
   - リクエストコストは低い

---

## 6. エンドポイント仕様

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

## 7. セキュリティ要件

AWS公式ベストプラクティスに基づく設計。

### 7.1 Pre-signed URL設定

| 設定項目 | 値 | 理由 |
|---------|-----|------|
| 有効期限 | 5分（300秒） | 最小限の有効期間で漏洩リスク軽減 |
| HTTPメソッド | PUT のみ | アップロード専用、読み取り不可 |
| Content-Type | 指定必須 | 予期しないファイルタイプを防止 |
| Content-Length | 上限10MB | DoS攻撃防止 |

### 7.2 S3バケット設定

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

### 7.3 IAMポリシー

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

### 7.4 CORS設定

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

## 8. クライアント実装ガイド（Next.js）

### 8.1 画像アップロード関数

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

### 8.2 料理登録フロー

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

## 9. エラーハンドリング

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

## 10. 障害パターンとリカバリ

各処理ステップで障害が発生した場合の振る舞いと復旧方法を定義する。

### 10.1 障害パターン一覧

| # | 障害発生箇所 | 状態 | 自動リカバリ | 備考 |
|---|-------------|------|:------------:|------|
| 1 | Pre-signed URL発行 | DBなし、S3なし | - | クライアントでリトライ |
| 2 | S3アップロード | DBなし、S3なしor一部あり | ✅ | 一時ファイルは24h後に自動削除 |
| 3 | S3存在確認 | DBなし、S3一時領域あり | ✅ | 一時ファイルは24h後に自動削除 |
| 4 | S3コピー（正式パスへ） | DBなし、S3一時領域あり | ✅ | 一時ファイルは24h後に自動削除 |
| 5 | DBトランザクション | S3正式パスあり、DBなし | ✅ | 孤立ファイルは定期バッチで削除 |
| 6 | 一時ファイル削除 | DB完了、S3正式パスあり | ✅ | 24h後に自動削除 |
| 7 | 旧ファイル削除 | DB完了、S3正式パスあり | ⚠️ | 定期バッチで削除推奨 |

### 10.2 各パターンの詳細

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

### 10.3 孤立ファイル削除バッチ（推奨実装）

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

### 10.4 設計原則

1. **S3操作はトランザクション外で実行**: S3は2フェーズコミット非対応
2. **ゴミは許容、不整合は許容しない**: S3に不要ファイルが残ることは許容するが、DBが参照するファイルが存在しない状態は許容しない
3. **自動クリーンアップを前提とした設計**: ライフサイクルルールと定期バッチでゴミを回収

---

## 11. 一時ファイルのクリーンアップ

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

## 12. 画像配信（CloudFront）

### 12.1 アーキテクチャ

```
┌────────┐     ┌────────────┐     ┌────────┐
│ Client │────>│ CloudFront │────>│   S3   │
└────────┘     └────────────┘     └────────┘
                    │
              署名付きURL
              キャッシュ
```

### 12.2 CloudFront設定

| 設定項目 | 値 | 説明 |
|---------|-----|------|
| オリジン | S3バケット（OAC経由） | 直接S3アクセス禁止 |
| キャッシュポリシー | CachingOptimized | 画像に最適化 |
| TTL | 最小1日、最大365日 | 長期キャッシュ |
| ビューワープロトコル | HTTPS only | セキュリティ |
| 価格クラス | PriceClass_200 | 日本含むアジア最適化 |

### 12.3 Origin Access Control (OAC)

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

### 12.4 署名付きURL生成（オプション）

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

### 12.5 レスポンスでの画像URL

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

## 13. 設定値一覧

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

## 14. 実装ファイル構成

```
app/features/dishes/
├── s3_service.py       # S3操作（Pre-signed URL生成、コピー、削除）
├── router.py           # POST /dishes/images/presigned-url 追加
├── schemas.py          # PresignedUrlRequest, PresignedUrlResponse 追加
└── exceptions.py       # InvalidContentTypeError 追加
```

---

## 15. モバイル実装ガイド

モバイルブラウザからの画像アップロードにおけるUX考慮点と推奨実装。

### 15.1 通信時間の目安

Pre-signed URL方式はサーバー経由方式より高速だが、モバイル回線では画像サイズが体験に大きく影響する。

| 画像サイズ | 4G回線での目安時間 | 備考 |
|-----------|-------------------|------|
| 500KB（圧縮後） | 1-2秒 | 推奨 |
| 2MB | 4-8秒 | やや遅い |
| 5MB（未圧縮） | 10秒以上 | UX低下 |

**処理時間の内訳（500KB想定）:**

| 処理 | 時間 |
|------|------|
| Pre-signed URL取得 | 100-300ms |
| S3アップロード | 1-2秒 |
| **合計** | **約2秒** |

### 15.2 懸念点と対策一覧

| 懸念 | 対策 |
|------|------|
| 画像サイズが大きい | クライアント側でリサイズ・圧縮 |
| アップロード進捗が見えない | プログレスバー表示 |
| 複数画像で時間がかかる | 並列アップロード |
| 通信が不安定 | リトライ処理 |

### 15.3 推奨：クライアント側での画像圧縮

アップロード前にリサイズすることで、通信時間を大幅に短縮できる。

```typescript
/**
 * 画像を指定サイズ以下にリサイズ・圧縮する
 * @param file - 元の画像ファイル
 * @param maxSize - 最大辺のピクセル数（デフォルト: 1200px）
 * @param quality - JPEG品質（0-1、デフォルト: 0.8）
 */
async function compressImage(
  file: File,
  maxSize: number = 1200,
  quality: number = 0.8
): Promise<Blob> {
  const canvas = document.createElement('canvas');
  const img = await createImageBitmap(file);

  // アスペクト比を維持してリサイズ
  const scale = Math.min(1, maxSize / Math.max(img.width, img.height));
  canvas.width = img.width * scale;
  canvas.height = img.height * scale;

  const ctx = canvas.getContext('2d');
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

  return new Promise(resolve =>
    canvas.toBlob(resolve, 'image/jpeg', quality)
  );
}

// 使用例
const compressedImage = await compressImage(originalFile);
// 元ファイル: 5MB → 圧縮後: 約300-500KB
```

### 15.4 推奨：プログレスバー表示

`XMLHttpRequest`を使用することで、アップロード進捗を取得できる。

```typescript
/**
 * 進捗表示付きでS3にアップロード
 * @param url - Pre-signed URL
 * @param file - アップロードするファイル
 * @param onProgress - 進捗コールバック（0-100）
 */
function uploadWithProgress(
  url: string,
  file: Blob,
  onProgress: (percent: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    // アップロード進捗イベント
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100);
        onProgress(percent);
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        reject(new Error(`Upload failed: ${xhr.status}`));
      }
    };

    xhr.onerror = () => reject(new Error('Network error'));

    xhr.open('PUT', url);
    xhr.setRequestHeader('Content-Type', file.type);
    xhr.send(file);
  });
}

// 使用例（React）
const [progress, setProgress] = useState(0);

await uploadWithProgress(presignedUrl, compressedImage, setProgress);
// UIでprogressを表示: <ProgressBar value={progress} />
```

### 15.5 推奨：複数画像の並列アップロード

複数画像は`Promise.all`で並列処理することで、総アップロード時間を短縮できる。

```typescript
async function uploadMultipleImages(
  files: File[],
  onTotalProgress: (percent: number) => void
): Promise<string[]> {
  const progressMap = new Map<number, number>();

  const updateTotalProgress = () => {
    const total = Array.from(progressMap.values()).reduce((a, b) => a + b, 0);
    onTotalProgress(Math.round(total / files.length));
  };

  const uploadPromises = files.map(async (file, index) => {
    // 1. 圧縮
    const compressed = await compressImage(file);

    // 2. Pre-signed URL取得
    const { upload_url, image_key } = await getPresignedUrl(compressed);

    // 3. アップロード（進捗追跡）
    await uploadWithProgress(upload_url, compressed, (percent) => {
      progressMap.set(index, percent);
      updateTotalProgress();
    });

    return image_key;
  });

  return Promise.all(uploadPromises);
}
```

### 15.6 推奨：リトライ処理

モバイル回線の不安定さに対応するため、指数バックオフでリトライを実装する。

```typescript
/**
 * 指数バックオフでリトライ
 * @param fn - 実行する非同期関数
 * @param maxRetries - 最大リトライ回数（デフォルト: 3）
 */
async function withRetry<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3
): Promise<T> {
  let lastError: Error;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;

      if (attempt < maxRetries - 1) {
        // 指数バックオフ: 1秒, 2秒, 4秒...
        const delay = Math.pow(2, attempt) * 1000;
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError;
}

// 使用例
const imageKey = await withRetry(() => uploadDishImage(file));
```

### 15.7 完全な実装例

上記の推奨事項をすべて組み込んだ実装例。

```typescript
interface UploadResult {
  image_key: string;
  display_order: number;
}

async function uploadDishImagesWithUX(
  files: File[],
  onProgress: (percent: number) => void,
  onStatus: (message: string) => void
): Promise<UploadResult[]> {
  const results: UploadResult[] = [];
  const progressMap = new Map<number, number>();

  const updateProgress = () => {
    const total = Array.from(progressMap.values()).reduce((a, b) => a + b, 0);
    onProgress(Math.round(total / files.length));
  };

  onStatus('画像を圧縮中...');

  const uploadPromises = files.map(async (file, index) => {
    // 1. 圧縮
    const compressed = await compressImage(file);
    progressMap.set(index, 10); // 圧縮完了で10%
    updateProgress();

    // 2. Pre-signed URL取得（リトライ付き）
    const { upload_url, image_key } = await withRetry(() =>
      getPresignedUrl(compressed)
    );
    progressMap.set(index, 20); // URL取得で20%
    updateProgress();

    // 3. アップロード（リトライ付き、進捗追跡）
    await withRetry(() =>
      uploadWithProgress(upload_url, compressed, (percent) => {
        // 20-100%の範囲で進捗を反映
        progressMap.set(index, 20 + percent * 0.8);
        updateProgress();
      })
    );

    return { image_key, display_order: index + 1 };
  });

  onStatus('アップロード中...');
  const uploadResults = await Promise.all(uploadPromises);

  onStatus('完了');
  return uploadResults;
}
```

---

## 参考資料

- [AWS S3 Pre-signed URL Documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)
- [AWS Pre-signed URL Best Practices](https://docs.aws.amazon.com/pdfs/prescriptive-guidance/latest/presigned-url-best-practices/presigned-url-best-practices.pdf)
- [Securing Amazon S3 presigned URLs for serverless applications](https://aws.amazon.com/blogs/compute/securing-amazon-s3-presigned-urls-for-serverless-applications/)
