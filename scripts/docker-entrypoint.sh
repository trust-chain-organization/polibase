#!/bin/bash
# Docker起動時のエントリーポイントスクリプト

# .venvディレクトリが無効な場合は削除して再作成
if [ -d "/app/.venv" ] && ! [ -f "/app/.venv/bin/python" ]; then
    echo "Invalid .venv directory detected, recreating..."
    rm -rf /app/.venv
    cd /app && uv sync --frozen
fi

# コマンドを実行
exec "$@"
