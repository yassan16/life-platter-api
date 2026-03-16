# life_platter-api ドキュメント

## 概要

このディレクトリには、life_platter-api プロジェクトの技術ドキュメントが格納されています。

## フォルダ構成

```
docs/
├── README.md                      # 本ファイル
├── architecture/
│   └── system-overview.md         # システム構成・Docker起動フロー
├── api/
│   └── error-handling.md          # エラーレスポンス共通仕様
├── features/
│   ├── auth/
│   │   ├── requirements.md        # 要件定義（Why/What）
│   │   ├── design.md              # 実装仕様・トークン仕様
│   │   ├── db-design.md           # refresh_tokens テーブル設計
│   │   └── token-guide.md         # 学習用：JWTの仕組み・2トークン方式の詳細解説
│   └── dish/
│       ├── requirements.md        # 要件定義（Why/What）
│       ├── design.md              # 実装仕様
│       ├── db-design.md           # dishes/dish_images テーブル設計
│       └── s3-image-upload.md     # S3 Pre-signed URL・CloudFront
└── setup/
    ├── commands.md                # Dockerコマンド・Alembic操作
    ├── migration-guide.md         # Alembicセットアップ詳細手順
    └── environment-variables.md   # 環境変数設定ガイド
```

## 各フォルダの概要

### アーキテクチャ (`docs/architecture/`)

- [architecture/system-overview.md](architecture/system-overview.md)
  - データベース接続フロー
  - リクエストフロー (Nginx → FastAPI → MySQL)
  - Docker 起動順序とシーケンス図

### 機能仕様 (`docs/features/`)

機能ごとに **要件定義層（requirements.md）** と **設計層（design.md）** の2層構成で管理。DB設計がある場合は **db-design.md** を追加。

| 層 | ファイル | 内容 |
|----|----------|------|
| 要件定義 | `requirements.md` | Why（目的）/ What（仕様）/ ユーザーストーリー |
| 設計 | `design.md` | 実装レベルの技術仕様・アーキテクチャ |
| DB設計 | `db-design.md` | テーブル定義・インデックス・削除ポリシー |

- 認証機能:
  - 要件定義: [features/auth/requirements.md](features/auth/requirements.md)
  - 設計: [features/auth/design.md](features/auth/design.md)（JWT + OAuth2 Password Flow、トークン仕様）
  - DB設計: [features/auth/db-design.md](features/auth/db-design.md)（refresh_tokens テーブル）
  - 学習用リファレンス: [features/auth/token-guide.md](features/auth/token-guide.md)（JWTの仕組み、2トークン方式の詳細解説）
- 料理機能:
  - 要件定義: [features/dish/requirements.md](features/dish/requirements.md)
  - 設計: [features/dish/design.md](features/dish/design.md)（CRUD API、画像差分更新、ページネーション）
  - DB設計: [features/dish/db-design.md](features/dish/db-design.md)（dishes/dish_images テーブル）
  - S3画像アップロード: [features/dish/s3-image-upload.md](features/dish/s3-image-upload.md)

### API共通仕様 (`docs/api/`)

- エラーレスポンス仕様: [api/error-handling.md](api/error-handling.md)
  - 統一エラーレスポンス型 (error_code, message, details)
  - レスポンス例

### 環境構築・運用 (`docs/setup/`)

- 基本コマンド一覧: [setup/commands.md](setup/commands.md)
- Alembicマイグレーションセットアップ: [setup/migration-guide.md](setup/migration-guide.md)
- 環境変数設定ガイド: [setup/environment-variables.md](setup/environment-variables.md)
