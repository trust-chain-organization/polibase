-- Migration: Add performance optimization indexes
-- Issue: #389 - Database query and LLM call optimization

-- 1. Add index on speakers.name for faster name searches
CREATE INDEX IF NOT EXISTS idx_speakers_name ON speakers(name);

-- 2. Add index on politicians.name for faster name searches
CREATE INDEX IF NOT EXISTS idx_politicians_name ON politicians(name);

-- 3. Add index on conversations.minutes_id for efficient joins with minutes table
-- This allows efficient retrieval of meeting_id through the minutes table
CREATE INDEX IF NOT EXISTS idx_conversations_minutes_id ON conversations(minutes_id);

-- 4. Add index on meetings.date for ordering and range queries
CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings(date DESC);

-- 5. Add composite index on politicians for party-based queries
CREATE INDEX IF NOT EXISTS idx_politicians_party_name ON politicians(political_party_id, name);

-- 6. Add composite index on speakers for type and party queries
CREATE INDEX IF NOT EXISTS idx_speakers_type_party ON speakers(type, political_party_name);

-- 7. Add index for speaker linking status queries
CREATE INDEX IF NOT EXISTS idx_conversations_speaker_linked ON conversations(speaker_id)
WHERE speaker_id IS NOT NULL;

-- 8. Add index for unprocessed minutes queries
CREATE INDEX IF NOT EXISTS idx_minutes_processed_status ON minutes(processed_at)
WHERE processed_at IS NULL;

-- 9. Add composite index for meeting filters
CREATE INDEX IF NOT EXISTS idx_meetings_conference_date ON meetings(conference_id, date DESC);

-- 10. Add index for politician speaker relationship
-- CREATE INDEX IF NOT EXISTS idx_politicians_speaker_party ON politicians(speaker_id, political_party_id);
-- Note: speaker_id column was removed from politicians table in migration 032

-- Performance note: These indexes will improve query performance for:
-- - Speaker name searches (reduces full table scans)
-- - Politician name searches (reduces full table scans)
-- - Meeting date-based queries (improves sorting and filtering)
-- - Party-based politician queries (reduces N+1 issues)
-- - Speaker linking status checks (partial index for efficiency)
