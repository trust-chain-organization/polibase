#!/bin/bash
set -e

echo "================================================"
echo "会議体メンバー管理機能 基本テスト"
echo "================================================"

# テスト用データ
TEST_CONFERENCE_ID=185  # 市会運営委員会

echo ""
echo "1. 会議体のURL設定状況を確認"
echo "------------------------------------------------"
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT c.id, c.name, gb.name as governing_body,
       CASE WHEN c.members_introduction_url IS NOT NULL THEN '設定済み' ELSE '未設定' END as url_status,
       c.members_introduction_url
FROM conferences c
JOIN governing_bodies gb ON c.governing_body_id = gb.id
WHERE c.id = $TEST_CONFERENCE_ID;"

echo ""
echo "2. ステップ1: メンバー抽出"
echo "------------------------------------------------"
echo "実行コマンド: docker compose exec polibase uv run polibase extract-conference-members --conference-id $TEST_CONFERENCE_ID"
docker compose exec polibase uv run polibase extract-conference-members --conference-id $TEST_CONFERENCE_ID

echo ""
echo "抽出結果の確認:"
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT matching_status, COUNT(*) as count
FROM extracted_conference_members
WHERE conference_id = $TEST_CONFERENCE_ID
GROUP BY matching_status;"

echo ""
echo "3. ステップ2: 政治家マッチング"
echo "------------------------------------------------"
echo "実行コマンド: docker compose exec polibase uv run polibase match-conference-members --conference-id $TEST_CONFERENCE_ID"
docker compose exec polibase uv run polibase match-conference-members --conference-id $TEST_CONFERENCE_ID

echo ""
echo "マッチング結果の確認:"
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT matching_status, COUNT(*) as count,
       AVG(matching_confidence)::numeric(3,2) as avg_confidence
FROM extracted_conference_members
WHERE conference_id = $TEST_CONFERENCE_ID
GROUP BY matching_status;"

echo ""
echo "4. マッチング詳細（サンプル）"
echo "------------------------------------------------"
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT ecm.extracted_name, ecm.extracted_role,
       ecm.matching_status, ecm.matching_confidence,
       p.name as matched_politician
FROM extracted_conference_members ecm
LEFT JOIN politicians p ON ecm.matched_politician_id = p.id
WHERE ecm.conference_id = $TEST_CONFERENCE_ID
ORDER BY ecm.matching_status DESC, ecm.matching_confidence DESC
LIMIT 10;"

echo ""
echo "5. ステップ3: 所属作成"
echo "------------------------------------------------"
echo "実行コマンド: docker compose exec polibase uv run polibase create-affiliations --conference-id $TEST_CONFERENCE_ID --start-date 2024-01-01"
docker compose exec polibase uv run polibase create-affiliations --conference-id $TEST_CONFERENCE_ID --start-date 2024-01-01

echo ""
echo "作成された所属の確認:"
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT COUNT(*) as affiliation_count
FROM politician_affiliations
WHERE conference_id = $TEST_CONFERENCE_ID
  AND start_date = '2024-01-01';"

echo ""
echo "6. 最終的な所属状況"
echo "------------------------------------------------"
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT p.name as politician_name, pa.role, pa.start_date
FROM politician_affiliations pa
JOIN politicians p ON pa.politician_id = p.id
WHERE pa.conference_id = $TEST_CONFERENCE_ID
  AND pa.end_date IS NULL
ORDER BY pa.role, p.name
LIMIT 20;"

echo ""
echo "7. 全体のステータス確認"
echo "------------------------------------------------"
echo "実行コマンド: docker compose exec polibase uv run polibase member-status --conference-id $TEST_CONFERENCE_ID"
docker compose exec polibase uv run polibase member-status --conference-id $TEST_CONFERENCE_ID

echo ""
echo "================================================"
echo "テスト完了"
echo "================================================"
