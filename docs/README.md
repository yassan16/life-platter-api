# life_platter-api ドキュメント

## 概要

このディレクトリには、life_platter-api プロジェクトの技術ドキュメントが格納されています。

## フォルダ構成

```
docs/
├── README.md                 # 本ファイル（ドキュメント構成の説明）
├── project-structure.md      # プロジェクト全体の構成
├── api/                      # API共通仕様
│   ├── endpoints.md
│   └── error-handling.md
├── database/                 # データベース関連
│   └── migration-guide.md
├── features/                 # 機能別仕様
│   ├── auth/
│   │   ├── spec.md
│   │   └── token-guide.md
│   └── dish/
│       ├── api-spec.md
│       ├── db-design.md
│       └── s3-image-upload.md
└── setup/                    # 環境構築・運用
    ├── commands.md
    └── docker-compose-startup-flow.md
```

## 各フォルダの概要
### プロジェクト構成 (`docs/`)
- プロジェクト構成: [project-structure.md](project-structure.md)
  - ディレクトリ構造
  - 機能モジュールの責務

### 機能仕様 (`docs/features/`)
- 認証機能: [features/auth.md](features/auth.md)
  - JWT + OAuth2 Password Flow
  - ログイン・ログアウト・トークン更新
  - リフレッシュトークン管理
  - レート制限
- 料理機能: [features/dish/](features/dish/)
  - DB設計: [db-design.md](features/dish/db-design.md)
    - dishes, dish_images, dish_categories テーブル設計
    - 削除・更新ポリシー（dishesは論理削除、dish_imagesは物理削除）
  - API仕様: [api-spec.md](features/dish/api-spec.md)
    - CRUD API（POST/GET/PUT/DELETE /dishes）
    - 画像の差分更新方式（images_to_add / images_to_delete）
    - カーソルベースページネーション
    - S3・DB連携のトランザクション管理
  - S3画像アップロード: [s3-image-upload.md](features/dish/s3-image-upload.md)
    - Pre-signed URL方式
    - セキュリティ要件（IAM、CORS、ライフサイクル）
    - 障害パターンとリカバリ（孤立ファイル削除バッチ）
    - CloudFront経由の画像配信

### API共通仕様 (`docs/api/`)
- エンドポイント仕様: [api/endpoints.md](api/endpoints.md)
  - 実装済みエンドポイント一覧
  - URL設計パターン
  - 今後実装予定のエンドポイント
- エラーレスポンス仕様: [api/error-handling.md](api/error-handling.md)
  - 統一エラーレスポンス型 (error_code, message, details)
  - レスポンス例

### 環境構築・運用 (`docs/setup/`)
- 基本コマンド一覧: [setup/commands.md](setup/commands.md)
  - Docker操作（起動・停止・ログ確認）
  - API動作確認（Swagger UI、DB接続テスト）
  - マイグレーション操作（Alembic）
  - データベース直接操作
- Docker起動フロー・アーキテクチャ詳細: [setup/docker-compose-startup-flow.md](setup/docker-compose-startup-flow.md)
  - データベース接続フロー
  - リクエストフロー (Nginx → FastAPI → MySQL)
  - Docker起動順序とシーケンス図

### データベース (`docs/database/`)
- Alembicマイグレーションセットアップ: [database/migration-guide.md](database/migration-guide.md)
  - パッケージインストールから初期化まで
  - env.py・database.pyの非同期対応設定
  - モデル作成とマイグレーション実行フロー
  - トラブルシューティング
