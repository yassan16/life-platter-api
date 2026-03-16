---
name: feature-workflow
description: life_platter-api に新機能を追加する際の手順（要件定義→設計→実装→マイグレーション）
---

# 機能追加ワークフロー

## 手順

### 1. 要件定義 (`requirements.md`)

`docs/features/<feature>/requirements.md` を作成:
- Why（目的・背景）
- What（機能仕様・ユーザーストーリー）
- 機能要件・非機能要件

### 2. 設計 (`design.md`)

`docs/features/<feature>/design.md` を作成:
- アーキテクチャ概要（Mermaidで図示）
- 技術選定と理由
- コンポーネント設計（責務・依存方向）
- データフロー（sequenceDiagram）
- エンドポイント仕様（リクエスト/レスポンス例）
- エラーハンドリング方針

### 3. DB設計 (`db-design.md`)

テーブル定義がある場合は `docs/features/<feature>/db-design.md` を作成:
- テーブル定義（カラム・型・説明）
- インデックス
- 削除・更新ポリシー

### 4. 実装

`app/features/<feature>/` 配下にファイルを作成（責務に従い分割）:

| ファイル | 責務 |
|---------|------|
| `models.py` | SQLAlchemyモデル（テーブル定義） |
| `schemas.py` | Pydanticモデル（リクエスト/レスポンス） |
| `repository.py` | DB操作の抽象化 |
| `service.py` | ビジネスロジック |
| `router.py` | エンドポイント定義 |
| `exceptions.py` | 機能固有の例外 |

### 5. ルーター登録

`app/api/__init__.py` に `include_router()` を追加。
全エンドポイントは `/api` プレフィックス配下に配置。

### 6. マイグレーション

新規テーブルがある場合:
```bash
# モデルを app/features/__init__.py でインポート
# マイグレーションファイル生成
docker compose exec app alembic revision --autogenerate -m "add <feature> table"
# 内容を確認してから適用
docker compose exec app alembic upgrade head
```

## エラーハンドリング規約

@docs/api/error-handling.md
