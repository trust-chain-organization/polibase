#!/bin/bash

# 議員団メンバー抽出機能の動作検証スクリプト

set -e  # エラーが発生したら停止

echo "=== 議員団メンバー抽出機能 動作検証 ==="
echo ""

# 色付き出力用の関数
print_section() {
    echo -e "\n\033[1;34m=== $1 ===\033[0m"
}

print_success() {
    echo -e "\033[1;32m✓ $1\033[0m"
}

print_error() {
    echo -e "\033[1;31m✗ $1\033[0m"
}

print_info() {
    echo -e "\033[1;33m→ $1\033[0m"
}

# Docker環境チェック
print_section "環境チェック"
if docker compose ps | grep -q "polibase.*running"; then
    print_success "Docker Composeが起動しています"
else
    print_error "Docker Composeが起動していません"
    echo "docker compose up -d を実行してください"
    exit 1
fi

# データベース接続チェック
print_info "データベース接続を確認中..."
if docker compose exec polibase uv run python -c "from src.config.database import test_connection; test_connection()" > /dev/null 2>&1; then
    print_success "データベース接続OK"
else
    print_error "データベース接続エラー"
    exit 1
fi

# 1. 議員団一覧表示
print_section "1. 議員団一覧表示"
docker compose exec polibase uv run polibase list-parliamentary-groups

# 2. 議員団の状況確認
print_section "2. 議員団メンバー抽出状況確認"
docker compose exec polibase uv run polibase group-member-status

# テスト用議員団のID（立憲民主党京都市会議員団）
GROUP_ID=10

# 3. 既存データのクリーンアップ（オプション）
print_section "3. 既存データのクリーンアップ"
print_info "議員団ID $GROUP_ID の既存抽出データをクリアしますか？ (y/N)"
read -r CLEANUP
if [[ "$CLEANUP" =~ ^[Yy]$ ]]; then
    docker compose exec postgres psql -U polibase_user -d polibase_db -c \
        "DELETE FROM parliamentary_group_memberships WHERE parliamentary_group_id = $GROUP_ID;"
    docker compose exec postgres psql -U polibase_user -d polibase_db -c \
        "DELETE FROM extracted_parliamentary_group_members WHERE parliamentary_group_id = $GROUP_ID;"
    print_success "クリーンアップ完了"
fi

# 4. ステップ1: メンバー抽出
print_section "4. ステップ1: 議員団メンバー抽出"
print_info "議員団URLからメンバーを抽出中..."
docker compose exec polibase uv run polibase extract-group-members --group-id $GROUP_ID --force

# 抽出結果確認
print_info "抽出されたメンバーを確認中..."
docker compose exec postgres psql -U polibase_user -d polibase_db -t -c \
    "SELECT COUNT(*) FROM extracted_parliamentary_group_members WHERE parliamentary_group_id = $GROUP_ID;" | \
    xargs -I {} echo "抽出されたメンバー数: {}"

# 5. ステップ2: メンバーマッチング
print_section "5. ステップ2: 政治家とのマッチング"
print_info "抽出されたメンバーを既存の政治家とマッチング中..."
docker compose exec polibase uv run polibase match-group-members --group-id $GROUP_ID

# マッチング結果確認
print_info "マッチング結果を確認中..."
docker compose exec postgres psql -U polibase_user -d polibase_db -c \
    "SELECT matching_status, COUNT(*) as count
     FROM extracted_parliamentary_group_members
     WHERE parliamentary_group_id = $GROUP_ID
     GROUP BY matching_status;"

# 6. ステップ3: メンバーシップ作成
print_section "6. ステップ3: メンバーシップ作成"
print_info "マッチング済みメンバーからメンバーシップを作成中..."
docker compose exec polibase uv run polibase create-group-memberships --group-id $GROUP_ID

# 作成結果確認
print_info "作成されたメンバーシップを確認中..."
docker compose exec postgres psql -U polibase_user -d polibase_db -t -c \
    "SELECT COUNT(*) FROM parliamentary_group_memberships WHERE parliamentary_group_id = $GROUP_ID;" | \
    xargs -I {} echo "作成されたメンバーシップ数: {}"

# 7. 最終状態確認
print_section "7. 最終状態確認"
docker compose exec polibase uv run polibase group-member-status --group-id $GROUP_ID

# 8. データ詳細表示
print_section "8. 詳細データ表示"

print_info "抽出されたメンバー詳細:"
docker compose exec postgres psql -U polibase_user -d polibase_db -c \
    "SELECT
        extracted_name as 名前,
        extracted_role as 役職,
        matching_status as マッチング状態,
        matching_confidence as 信頼度
     FROM extracted_parliamentary_group_members
     WHERE parliamentary_group_id = $GROUP_ID
     ORDER BY extracted_name;"

print_info "作成されたメンバーシップ詳細:"
docker compose exec postgres psql -U polibase_user -d polibase_db -c \
    "SELECT
        p.name as 政治家名,
        pgm.role as 役職,
        pgm.start_date as 開始日
     FROM parliamentary_group_memberships pgm
     JOIN politicians p ON pgm.politician_id = p.id
     WHERE pgm.parliamentary_group_id = $GROUP_ID
     ORDER BY p.name;"

print_section "検証完了"
print_success "すべての機能が正常に動作しています"
