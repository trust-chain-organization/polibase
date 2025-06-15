#!/bin/bash
set -e

echo "================================================"
echo "政治家情報抽出機能 基本テスト"
echo "================================================"

# カラー定義
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo "1. 政党のURL設定状況を確認"
echo "------------------------------------------------"
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT id, name, members_list_url,
       CASE WHEN members_list_url IS NOT NULL THEN '設定済み' ELSE '未設定' END as status
FROM political_parties
ORDER BY id;"

echo ""
echo "2. 現在の政治家数を確認"
echo "------------------------------------------------"
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT pp.name as party_name, COUNT(p.id) as member_count
FROM political_parties pp
LEFT JOIN politicians p ON pp.id = p.political_party_id
GROUP BY pp.id, pp.name
ORDER BY pp.id;"

echo ""
echo "3. ドライランでテスト（保存しない）"
echo "------------------------------------------------"
TEST_PARTY_ID=2  # 立憲民主党でテスト
echo "実行コマンド: docker compose exec polibase uv run polibase scrape-politicians --party-id $TEST_PARTY_ID --dry-run"
docker compose exec polibase uv run polibase scrape-politicians --party-id $TEST_PARTY_ID --dry-run

echo ""
echo "4. 実際にスクレイピングを実行（1政党のみ）"
echo "------------------------------------------------"
read -p "政党ID $TEST_PARTY_ID のスクレイピングを実行しますか？ (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "実行コマンド: docker compose exec polibase uv run polibase scrape-politicians --party-id $TEST_PARTY_ID"
    docker compose exec polibase uv run polibase scrape-politicians --party-id $TEST_PARTY_ID

    echo ""
    echo "5. 新規追加された政治家を確認"
    echo "------------------------------------------------"
    docker compose exec postgres psql -U polibase_user -d polibase_db -c "
    SELECT p.name, pp.name as party_name, p.position, p.prefecture
    FROM politicians p
    JOIN political_parties pp ON p.political_party_id = pp.id
    WHERE p.political_party_id = $TEST_PARTY_ID
      AND p.created_at >= CURRENT_TIMESTAMP - INTERVAL '5 minutes'
    ORDER BY p.created_at DESC
    LIMIT 10;"
else
    echo -e "${RED}スキップされました${NC}"
fi

echo ""
echo "6. 重複チェック"
echo "------------------------------------------------"
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT name, political_party_id, COUNT(*) as count
FROM politicians
GROUP BY name, political_party_id
HAVING COUNT(*) > 1
LIMIT 10;"

DUPLICATE_COUNT=$(docker compose exec postgres psql -U polibase_user -d polibase_db -t -c "
SELECT COUNT(*)
FROM (
    SELECT name, political_party_id
    FROM politicians
    GROUP BY name, political_party_id
    HAVING COUNT(*) > 1
) as duplicates;")

if [ "$DUPLICATE_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓ 重複なし${NC}"
else
    echo -e "${RED}✗ $DUPLICATE_COUNT 件の重複が見つかりました${NC}"
fi

echo ""
echo "================================================"
echo "テスト完了"
echo "================================================"

echo ""
echo "次のステップ:"
echo "1. すべての政党をスクレイピングする場合:"
echo "   docker compose exec polibase uv run polibase scrape-politicians --all-parties"
echo "2. StreamlitでURLを管理する場合:"
echo "   docker compose exec polibase uv run polibase streamlit"
