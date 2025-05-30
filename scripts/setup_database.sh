#!/bin/bash

# Docker Compose環境のセットアップと動作確認用スクリプト

echo "Docker Compose環境をビルドしています..."
docker compose build

echo "PostgreSQLを含む全サービスを起動しています..."
docker compose up -d

echo "PostgreSQLの準備完了を待機しています..."
sleep 10

echo "データベース接続をテストしています..."
docker compose exec polibase python -m src.config.database

echo "PostgreSQLデータベースの状態を確認しています..."
docker compose exec postgres psql -U polibase_user -d polibase_db -c "\dt"

echo "テーブル作成状況を確認しています..."
docker compose exec postgres psql -U polibase_user -d polibase_db -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"

echo "設定完了！以下のコマンドでコンテナにアクセスできます："
echo "docker compose exec polibase bash"
echo "docker compose exec postgres psql -U polibase_user -d polibase_db"
