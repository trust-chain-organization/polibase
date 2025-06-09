FROM python:3.13-slim

# PostgreSQLクライアントとPlaywrightの依存関係をインストール
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    # Playwright用の依存関係
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libglib2.0-0 \
    libexpat1 \
    libxtst6 \
    libxss1 \
    fonts-liberation \
    libappindicator3-1 \
    libnss3-dev \
    libgdk-pixbuf2.0-0 \
    libgtk-3-0 \
    libxshmfence1 \
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

# Playwrightのブラウザをインストール
RUN uv run playwright install chromium

# アプリケーションファイルをコピー
COPY src/ src/
COPY database/ database/
COPY scripts/ scripts/
COPY backup-database.sh test-setup.sh reset-database.sh ./

# コンテナ起動時に実行するコマンド
CMD ["/bin/bash"]
# CMD ["poetry", "run", "python", "main.py"]
