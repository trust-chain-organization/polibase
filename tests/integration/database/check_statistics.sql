-- Polibase データベース統計レポート
-- ================================================

-- 1. テーブル別レコード数とサイズ
\echo '================================================'
\echo 'テーブル別統計'
\echo '================================================'

SELECT
    schemaname,
    tablename,
    n_live_tup as row_count,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) as indexes_size
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;

-- 2. データベース全体のサイズ
\echo ''
\echo '================================================'
\echo 'データベースサイズ'
\echo '================================================'

SELECT
    pg_database_size('polibase_db') as size_bytes,
    pg_size_pretty(pg_database_size('polibase_db')) as size_pretty;

-- 3. 政治家データの統計
\echo ''
\echo '================================================'
\echo '政治家データ統計'
\echo '================================================'

SELECT
    pp.name as party_name,
    COUNT(p.id) as member_count,
    COUNT(DISTINCT p.prefecture) as prefecture_count
FROM political_parties pp
LEFT JOIN politicians p ON pp.id = p.political_party_id
GROUP BY pp.id, pp.name
ORDER BY member_count DESC;

-- 4. 会議データの統計
\echo ''
\echo '================================================'
\echo '会議データ統計'
\echo '================================================'

SELECT
    gb.name as governing_body,
    COUNT(DISTINCT c.id) as conference_count,
    COUNT(m.id) as meeting_count,
    MIN(m.date) as oldest_meeting,
    MAX(m.date) as newest_meeting
FROM governing_bodies gb
LEFT JOIN conferences c ON gb.id = c.governing_body_id
LEFT JOIN meetings m ON c.id = m.conference_id
GROUP BY gb.id, gb.name
ORDER BY meeting_count DESC;

-- 5. 発言データの統計
\echo ''
\echo '================================================'
\echo '発言データ統計'
\echo '================================================'

SELECT
    COUNT(*) as total_conversations,
    COUNT(DISTINCT meeting_id) as unique_meetings,
    COUNT(DISTINCT speaker_id) as unique_speakers,
    COUNT(CASE WHEN speaker_id IS NULL THEN 1 END) as unlinked_conversations,
    AVG(LENGTH(content)) as avg_content_length
FROM conversations;

-- 6. スクレイピングデータの統計
\echo ''
\echo '================================================'
\echo 'スクレイピング統計'
\echo '================================================'

SELECT
    DATE(created_at) as date,
    COUNT(*) as total_scraped,
    COUNT(gcs_pdf_uri) as with_pdf,
    COUNT(gcs_text_uri) as with_text,
    COUNT(CASE WHEN gcs_pdf_uri IS NULL AND gcs_text_uri IS NULL THEN 1 END) as failed
FROM meetings
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC
LIMIT 10;

-- 7. 議員団データの統計
\echo ''
\echo '================================================'
\echo '議員団データ統計'
\echo '================================================'

SELECT
    pg.name as group_name,
    COUNT(pgm.id) as member_count,
    pg.url
FROM parliamentary_groups pg
LEFT JOIN parliamentary_group_memberships pgm ON pg.id = pgm.parliamentary_group_id
GROUP BY pg.id, pg.name, pg.url
ORDER BY member_count DESC;

-- 8. 会議体メンバーの統計
\echo ''
\echo '================================================'
\echo '会議体メンバー統計'
\echo '================================================'

SELECT
    c.name as conference_name,
    COUNT(pa.id) as current_members,
    COUNT(DISTINCT pa.politician_id) as unique_politicians
FROM conferences c
LEFT JOIN politician_affiliations pa ON c.id = pa.conference_id
    AND pa.end_date IS NULL
GROUP BY c.id, c.name
HAVING COUNT(pa.id) > 0
ORDER BY current_members DESC
LIMIT 10;

-- 9. データ品質チェック
\echo ''
\echo '================================================'
\echo 'データ品質チェック'
\echo '================================================'

-- 必須フィールドのNULLチェック
SELECT
    'politicians.name' as check_item,
    COUNT(*) as null_count
FROM politicians WHERE name IS NULL
UNION ALL
SELECT 'meetings.date', COUNT(*)
FROM meetings WHERE date IS NULL
UNION ALL
SELECT 'conferences.name', COUNT(*)
FROM conferences WHERE name IS NULL
UNION ALL
SELECT 'political_parties.name', COUNT(*)
FROM political_parties WHERE name IS NULL;

-- 10. 最近の活動
\echo ''
\echo '================================================'
\echo '最近の活動（過去24時間）'
\echo '================================================'

SELECT
    'meetings' as table_name,
    COUNT(*) as new_records
FROM meetings
WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
UNION ALL
SELECT 'politicians', COUNT(*)
FROM politicians
WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
UNION ALL
SELECT 'conversations', COUNT(*)
FROM conversations
WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours';
