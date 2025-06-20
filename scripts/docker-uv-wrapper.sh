#!/bin/bash
# Docker container内でuvコマンドを実行するためのラッパースクリプト
# 仮想環境の作成を防ぐため、--no-projectフラグを自動的に追加

if [ "$1" = "run" ]; then
    # uv runの場合は--no-projectフラグを追加
    uv run --no-project "${@:2}"
else
    # その他のuvコマンドはそのまま実行
    uv "$@"
fi
