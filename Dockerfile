# 1. ベースイメージ: Python 3.12 (軽量版のslim)
FROM python:3.12-slim

# 2. PythonがDocker内で安全に動くための設定
# .pycファイル(キャッシュ)を作らせない
ENV PYTHONDONTWRITEBYTECODE=1
# ログを溜め込まず、すぐにコンソールに出力させる
ENV PYTHONUNBUFFERED=1

# 3. 作業ディレクトリの作成（ここが質問の箇所です）
WORKDIR /app

# 4. 依存ライブラリのインストール
# 先にrequirements.txtだけをコピー
COPY requirements.txt .
# ライブラリをインストール
RUN pip install --no-cache-dir -r requirements.txt

# 5. ソースコードをすべてコピー
COPY . .

# 6. アプリケーションの起動
# ホスト0.0.0.0で公開し、コード変更を検知して再起動(--reload)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]