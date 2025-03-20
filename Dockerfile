FROM python:3.9-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なファイルをコピー
COPY pyproject.toml poetry.lock ./

# Poetryをインストール
RUN pip install poetry

# 依存関係をインストール
RUN poetry install --no-root

# 必要なファイルをコピー
COPY main.py main.py
COPY config.py config.py
COPY utils/ utils/

# コンテナ起動時に実行するコマンド
CMD ["/bin/bash"]
# CMD ["poetry", "run", "python", "main.py"]
