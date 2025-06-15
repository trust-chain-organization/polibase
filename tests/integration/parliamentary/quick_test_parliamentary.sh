#!/bin/bash

# 議員団メンバー抽出機能のクイックテスト

echo "=== 議員団メンバー抽出 クイックテスト ==="
echo ""

# 1. 議員団一覧
echo "1. 議員団一覧:"
docker compose exec polibase uv run polibase list-parliamentary-groups | head -20

echo ""
echo "2. 抽出状況:"
docker compose exec polibase uv run polibase group-member-status | head -20

echo ""
echo "3. データベース状況:"
docker compose exec postgres psql -U polibase_user -d polibase_db -t -c "
SELECT
    'parliamentary_groups' as table_name, COUNT(*) as count
FROM parliamentary_groups
UNION ALL
SELECT
    'extracted_members' as table_name, COUNT(*) as count
FROM extracted_parliamentary_group_members
UNION ALL
SELECT
    'memberships' as table_name, COUNT(*) as count
FROM parliamentary_group_memberships
UNION ALL
SELECT
    'politicians' as table_name, COUNT(*) as count
FROM politicians;"

echo ""
echo "✓ クイックテスト完了"
