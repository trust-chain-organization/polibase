#!/bin/bash
set -e

echo "================================================"
echo "スクレイピング機能 基本テスト"
echo "================================================"

# カラー定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

# テスト用URL（実際のURLに置き換えてください）
TEST_URL="https://ssp.kaigiroku.net/tenant/kyoto/SpMinuteView.html?council_id=123&schedule_id=456"
TEST_TENANT="kyoto"

echo ""
echo "1. GCS設定の確認"
echo "------------------------------------------------"
if [ -n "$GCS_BUCKET_NAME" ]; then
    echo -e "${GREEN}✓ GCS_BUCKET_NAME: $GCS_BUCKET_NAME${NC}"
else
    echo -e "${YELLOW}⚠ GCS_BUCKET_NAME が設定されていません${NC}"
fi

echo ""
echo "2. 単一議事録のスクレイピングテスト"
echo "------------------------------------------------"
echo "テストURL: $TEST_URL"
echo ""
read -p "このURLでスクレイピングを実行しますか？ (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "実行コマンド: docker compose exec polibase uv run polibase scrape-minutes \"$TEST_URL\""
    docker compose exec polibase uv run polibase scrape-minutes "$TEST_URL"

    # 結果確認
    echo ""
    echo "スクレイピング結果:"
    docker compose exec postgres psql -U polibase_user -d polibase_db -c "
    SELECT m.id, m.date, m.url,
           CASE WHEN m.gcs_pdf_uri IS NOT NULL THEN '✓' ELSE '✗' END as pdf,
           CASE WHEN m.gcs_text_uri IS NOT NULL THEN '✓' ELSE '✗' END as text
    FROM meetings m
    WHERE m.url = '$TEST_URL'
    ORDER BY m.created_at DESC
    LIMIT 1;"
else
    echo -e "${YELLOW}スキップされました${NC}"
fi

echo ""
echo "3. GCSアップロード付きスクレイピング"
echo "------------------------------------------------"
if [ -n "$GCS_BUCKET_NAME" ]; then
    echo "実行コマンド: docker compose exec polibase uv run polibase scrape-minutes \"$TEST_URL\" --upload-to-gcs"
    read -p "GCSアップロードを含むテストを実行しますか？ (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker compose exec polibase uv run polibase scrape-minutes "$TEST_URL" --upload-to-gcs

        # GCS URIの確認
        echo ""
        echo "GCS URI確認:"
        docker compose exec postgres psql -U polibase_user -d polibase_db -c "
        SELECT m.gcs_pdf_uri, m.gcs_text_uri
        FROM meetings m
        WHERE m.url = '$TEST_URL'
        ORDER BY m.created_at DESC
        LIMIT 1;"
    else
        echo -e "${YELLOW}スキップされました${NC}"
    fi
else
    echo -e "${YELLOW}GCS設定がないためスキップ${NC}"
fi

echo ""
echo "4. バッチスクレイピングのテスト"
echo "------------------------------------------------"
echo "テスト自治体: $TEST_TENANT"
echo "最新5件を取得します"
echo ""
read -p "バッチスクレイピングを実行しますか？ (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "実行コマンド: docker compose exec polibase uv run polibase batch-scrape --tenant $TEST_TENANT --limit 5"
    docker compose exec polibase uv run polibase batch-scrape --tenant $TEST_TENANT --limit 5

    # 結果確認
    echo ""
    echo "バッチスクレイピング結果:"
    docker compose exec postgres psql -U polibase_user -d polibase_db -c "
    SELECT m.date, c.name as conference,
           CASE WHEN m.gcs_pdf_uri IS NOT NULL THEN '✓' ELSE '✗' END as pdf,
           CASE WHEN m.gcs_text_uri IS NOT NULL THEN '✓' ELSE '✗' END as text
    FROM meetings m
    JOIN conferences c ON m.conference_id = c.id
    JOIN governing_bodies gb ON c.governing_body_id = gb.id
    WHERE gb.name LIKE '%京都%'
    ORDER BY m.created_at DESC
    LIMIT 5;"
else
    echo -e "${YELLOW}スキップされました${NC}"
fi

echo ""
echo "5. ローカルファイルの確認"
echo "------------------------------------------------"
if [ -d "data/scraped" ]; then
    echo "最近のスクレイピングファイル:"
    find data/scraped -type f -name "*.txt" -o -name "*.pdf" | head -10

    TOTAL_FILES=$(find data/scraped -type f | wc -l)
    TOTAL_SIZE=$(du -sh data/scraped 2>/dev/null | cut -f1)
    echo ""
    echo "合計: $TOTAL_FILES ファイル ($TOTAL_SIZE)"
else
    echo "data/scraped ディレクトリが見つかりません"
fi

echo ""
echo "6. エラー状況の確認"
echo "------------------------------------------------"
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT DATE(created_at) as date, COUNT(*) as error_count
FROM meetings
WHERE url LIKE '%kaigiroku.net%'
  AND gcs_pdf_uri IS NULL
  AND gcs_text_uri IS NULL
  AND created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;"

echo ""
echo "================================================"
echo "テスト完了"
echo "================================================"

echo ""
echo "追加テストオプション:"
echo "- 国会議事録: docker compose exec polibase uv run polibase scrape-minutes \"https://kokkai.ndl.go.jp/...\""
echo "- 他の自治体: docker compose exec polibase uv run polibase batch-scrape --tenant osaka"
echo "- GCS確認: gsutil ls -la gs://\$GCS_BUCKET_NAME/scraped/"
