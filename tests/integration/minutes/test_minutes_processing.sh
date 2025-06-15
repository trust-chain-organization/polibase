#!/bin/bash
set -e

echo "================================================"
echo "議事録処理機能 基本テスト"
echo "================================================"

# テスト用データ
TEST_MEETING_ID=1

echo ""
echo "1. テストデータの確認"
echo "------------------------------------------------"
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT m.id, m.date, m.gcs_text_uri, gb.name as governing_body, c.name as conference
FROM meetings m
JOIN conferences c ON m.conference_id = c.id
JOIN governing_bodies gb ON c.governing_body_id = gb.id
WHERE m.id = $TEST_MEETING_ID;"

echo ""
echo "2. 議事録分割処理の実行"
echo "------------------------------------------------"
echo "実行コマンド: docker compose exec polibase uv run python -m src.process_minutes --meeting-id $TEST_MEETING_ID"
docker compose exec polibase uv run python -m src.process_minutes --meeting-id $TEST_MEETING_ID

echo ""
echo "3. 発言記録の確認"
echo "------------------------------------------------"
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT COUNT(*) as conversation_count
FROM conversations
WHERE meeting_id = $TEST_MEETING_ID;"

echo ""
echo "4. 発言者抽出の実行"
echo "------------------------------------------------"
echo "実行コマンド: docker compose exec polibase uv run polibase extract-speakers"
docker compose exec polibase uv run polibase extract-speakers

echo ""
echo "5. 発言者の確認"
echo "------------------------------------------------"
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT COUNT(DISTINCT s.id) as speaker_count
FROM speakers s
JOIN conversations c ON s.id = c.speaker_id
WHERE c.meeting_id = $TEST_MEETING_ID;"

echo ""
echo "6. 発言者マッチングの実行"
echo "------------------------------------------------"
echo "実行コマンド: docker compose exec polibase uv run polibase update-speakers --use-llm"
docker compose exec polibase uv run polibase update-speakers --use-llm

echo ""
echo "7. マッチング結果の確認"
echo "------------------------------------------------"
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT s.name as speaker_name, p.name as politician_name
FROM speakers s
LEFT JOIN politicians p ON s.politician_id = p.id
WHERE s.id IN (
    SELECT DISTINCT speaker_id
    FROM conversations
    WHERE meeting_id = $TEST_MEETING_ID AND speaker_id IS NOT NULL
)
LIMIT 10;"

echo ""
echo "================================================"
echo "テスト完了"
echo "================================================"
