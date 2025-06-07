#!/bin/bash
# PostgreSQLデータベース バックアップ/リストア スクリプト

BACKUP_DIR="./database/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="polibase_backup_${TIMESTAMP}.sql"

# バックアップディレクトリが存在しない場合は作成
mkdir -p "$BACKUP_DIR"

# 使用方法を表示する関数
show_usage() {
    echo "🗄️  Polibase データベース バックアップ/リストア"
    echo "=============================================="
    echo ""
    echo "使用方法:"
    echo "  $0 backup                    # データベースをバックアップ"
    echo "  $0 restore <backup_file>     # バックアップからリストア"
    echo "  $0 list                      # バックアップファイル一覧"
    echo ""
    echo "例:"
    echo "  $0 backup"
    echo "  $0 restore database/backups/polibase_backup_20240529_123456.sql"
    echo "  $0 list"
}

# バックアップ作成
backup_database() {
    echo "💾 データベースをバックアップ中..."

    # PostgreSQLが起動しているか確認
    if ! docker compose ps postgres | grep -q "Up"; then
        echo "❌ PostgreSQLコンテナが起動していません"
        echo "以下のコマンドでDockerサービスを起動してください："
        echo "docker compose up -d"
        exit 1
    fi

    # バックアップ実行
    docker compose exec -T postgres pg_dump -U polibase_user polibase_db > "$BACKUP_DIR/$BACKUP_FILE"

    if [ $? -eq 0 ]; then
        echo "✅ バックアップ完了: $BACKUP_DIR/$BACKUP_FILE"
        echo "📊 バックアップサイズ: $(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)"
    else
        echo "❌ バックアップに失敗しました"
        exit 1
    fi
}

# リストア実行
restore_database() {
    local backup_file="$1"

    if [ -z "$backup_file" ]; then
        echo "❌ バックアップファイルを指定してください"
        show_usage
        exit 1
    fi

    if [ ! -f "$backup_file" ]; then
        echo "❌ バックアップファイルが見つかりません: $backup_file"
        exit 1
    fi

    echo "⚠️  警告: この操作は現在のデータベースを上書きします"
    echo "リストアファイル: $backup_file"
    echo ""
    read -p "本当に実行しますか？ (y/N): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 操作をキャンセルしました"
        exit 0
    fi

    echo "📥 データベースをリストア中..."

    # PostgreSQLが起動しているか確認
    if ! docker compose ps postgres | grep -q "Up"; then
        echo "❌ PostgreSQLコンテナが起動していません"
        echo "以下のコマンドでDockerサービスを起動してください："
        echo "docker compose up -d"
        exit 1
    fi

    # 既存のデータベースを削除して再作成
    docker compose exec -T postgres psql -U polibase_user -d postgres -c "DROP DATABASE IF EXISTS polibase_db;"
    docker compose exec -T postgres psql -U polibase_user -d postgres -c "CREATE DATABASE polibase_db;"

    # リストア実行
    docker compose exec -T postgres psql -U polibase_user -d polibase_db < "$backup_file"

    if [ $? -eq 0 ]; then
        echo "✅ リストア完了"
        echo "🔍 データベース状態を確認中..."
        docker compose exec -T postgres psql -U polibase_user -d polibase_db -c "\dt"
    else
        echo "❌ リストアに失敗しました"
        exit 1
    fi
}

# バックアップファイル一覧
list_backups() {
    echo "📋 バックアップファイル一覧"
    echo "=========================="

    if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A "$BACKUP_DIR" 2>/dev/null)" ]; then
        echo "バックアップファイルが見つかりません"
        return
    fi

    ls -la "$BACKUP_DIR"/*.sql 2>/dev/null | while read -r line; do
        echo "$line"
    done
}

# メイン処理
case "$1" in
    backup)
        backup_database
        ;;
    restore)
        restore_database "$2"
        ;;
    list)
        list_backups
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
