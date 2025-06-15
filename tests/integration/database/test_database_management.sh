#!/bin/bash
set -e

echo "================================================"
echo "データベース管理機能 基本テスト"
echo "================================================"

# カラー定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

# バックアップディレクトリ
BACKUP_DIR="database/backups"

echo ""
echo "1. データベース接続テスト"
echo "------------------------------------------------"
docker compose exec polibase uv run python -c "from src.config.database import test_connection; test_connection()"

echo ""
echo "2. 現在のデータベース状態"
echo "------------------------------------------------"
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT
    schemaname,
    tablename,
    n_live_tup as row_count
FROM pg_stat_user_tables
WHERE n_live_tup > 0
ORDER BY n_live_tup DESC
LIMIT 10;"

echo ""
echo "データベースサイズ:"
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT
    pg_database_size('polibase_db') as size_bytes,
    pg_size_pretty(pg_database_size('polibase_db')) as size_pretty;"

echo ""
echo "3. バックアップテスト（ローカル）"
echo "------------------------------------------------"
echo "実行コマンド: docker compose exec polibase uv run polibase database backup --no-gcs"
docker compose exec polibase uv run polibase database backup --no-gcs

# 最新のバックアップファイルを確認
LATEST_BACKUP=$(ls -t $BACKUP_DIR/backup_*.sql 2>/dev/null | head -1)
if [ -n "$LATEST_BACKUP" ]; then
    echo -e "${GREEN}✓ バックアップ作成成功: $LATEST_BACKUP${NC}"
    BACKUP_SIZE=$(ls -lh "$LATEST_BACKUP" | awk '{print $5}')
    echo "  サイズ: $BACKUP_SIZE"
else
    echo -e "${RED}✗ バックアップファイルが見つかりません${NC}"
fi

echo ""
echo "4. バックアップ一覧"
echo "------------------------------------------------"
echo "実行コマンド: docker compose exec polibase uv run polibase database list --no-gcs"
docker compose exec polibase uv run polibase database list --no-gcs

echo ""
echo "5. GCS統合テスト"
echo "------------------------------------------------"
if [ -n "$GCS_BUCKET_NAME" ]; then
    echo -e "${GREEN}GCS設定あり: $GCS_BUCKET_NAME${NC}"

    read -p "GCSへのバックアップを実行しますか？ (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "実行コマンド: docker compose exec polibase uv run polibase database backup"
        docker compose exec polibase uv run polibase database backup

        echo ""
        echo "GCSバックアップ一覧:"
        docker compose exec polibase uv run polibase database list
    else
        echo -e "${YELLOW}スキップされました${NC}"
    fi
else
    echo -e "${YELLOW}GCS設定なし${NC}"
fi

echo ""
echo "6. マイグレーション確認"
echo "------------------------------------------------"
echo "適用済みマイグレーション:"
ls -1 database/migrations/*.sql | sort | while read migration; do
    filename=$(basename "$migration")
    # マイグレーションが適用されているかチェック（簡易的）
    if docker compose exec postgres psql -U polibase_user -d polibase_db -c "\dt" | grep -q "extracted_conference_members"; then
        echo -e "${GREEN}✓${NC} $filename"
    else
        echo -e "${YELLOW}?${NC} $filename"
    fi
done

echo ""
echo "7. データ整合性チェック"
echo "------------------------------------------------"
# 外部キー制約の確認
echo "外部キー制約違反チェック:"
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT
    conname as constraint_name,
    conrelid::regclass as table_name,
    confrelid::regclass as referenced_table
FROM pg_constraint
WHERE contype = 'f'
  AND NOT EXISTS (
    SELECT 1 FROM pg_constraint c2
    WHERE c2.conname = pg_constraint.conname
      AND c2.connamespace = pg_constraint.connamespace
  )
LIMIT 5;"

# NULLチェック
echo ""
echo "必須フィールドのNULLチェック:"
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT 'politicians' as table_name, COUNT(*) as null_count
FROM politicians WHERE name IS NULL
UNION ALL
SELECT 'meetings', COUNT(*)
FROM meetings WHERE date IS NULL
UNION ALL
SELECT 'conferences', COUNT(*)
FROM conferences WHERE name IS NULL;"

echo ""
echo "8. リストアテスト（オプション）"
echo "------------------------------------------------"
if [ -n "$LATEST_BACKUP" ]; then
    echo -e "${YELLOW}警告: リストアはデータベースを上書きします${NC}"
    read -p "最新のバックアップからリストアしますか？ (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        BACKUP_FILENAME=$(basename "$LATEST_BACKUP")
        echo "実行コマンド: docker compose exec polibase uv run polibase database restore $BACKUP_FILENAME"
        docker compose exec polibase uv run polibase database restore "$BACKUP_FILENAME"
        echo -e "${GREEN}✓ リストア完了${NC}"
    else
        echo -e "${YELLOW}スキップされました${NC}"
    fi
else
    echo "リストア可能なバックアップがありません"
fi

echo ""
echo "================================================"
echo "テスト完了"
echo "================================================"

echo ""
echo "追加コマンド:"
echo "- データベースリセット: ./reset-database.sh"
echo "- 手動バックアップ: ./backup-database.sh backup"
echo "- 統計情報: docker compose exec postgres psql -U polibase_user -d polibase_db -c \"\\l+\""
