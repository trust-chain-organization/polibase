FROM python:3.13-slim

# PostgreSQLクライアントのインストール
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリを設定
WORKDIR /app

# uvを公式インストーラーでインストール
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# uvをPATHに追加
ENV PATH="/root/.local/bin:$PATH"

# 必要なファイルをコピー（順序が重要）
COPY README.md ./
COPY pyproject.toml uv.lock ./

# 依存関係をインストール
RUN uv sync

# アプリケーションファイルをコピー
COPY src/ src/
COPY database/ database/
COPY scripts/ scripts/
COPY backup-database.sh test-setup.sh reset-database.sh ./

# コンテナ起動時に実行するコマンド
CMD ["/bin/bash"]
# CMD ["poetry", "run", "python", "main.py"]
