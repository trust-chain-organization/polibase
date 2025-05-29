FROM python:3.13-slim

# PostgreSQLクライアントのインストール
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリを設定
WORKDIR /app

# 必要なファイルをコピー
COPY pyproject.toml uv.lock ./

# uvをインストール
RUN pip install uv

# 依存関係をインストール
RUN uv sync

# 必要なファイルをコピー
COPY src/ src/
COPY database/ database/

# コンテナ起動時に実行するコマンド
CMD ["/bin/bash"]
# CMD ["poetry", "run", "python", "main.py"]
