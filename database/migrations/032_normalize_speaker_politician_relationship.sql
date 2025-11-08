-- Normalize Speaker-Politician relationship
-- Change from politicians.speaker_id to speakers.politician_id to support 1-to-many relationship
-- A single politician can have multiple speaker representations in meeting minutes

-- Step 1: Add politician_id column to speakers table
ALTER TABLE speakers ADD COLUMN IF NOT EXISTS politician_id INTEGER REFERENCES politicians(id);

-- Create index for efficient lookup
CREATE INDEX IF NOT EXISTS idx_speakers_politician_id ON speakers(politician_id);

-- Step 2: Migrate existing data from politicians.speaker_id to speakers.politician_id
-- UPDATE speakers s
-- SET politician_id = p.id
-- FROM politicians p
-- WHERE p.speaker_id = s.id
--   AND p.speaker_id IS NOT NULL;
-- Note: This migration is skipped because speaker_id column is not present in init.sql anymore

-- Step 3: Drop speaker_id from politicians table
ALTER TABLE politicians DROP COLUMN IF EXISTS speaker_id;

-- Add comments to clarify the new relationship
COMMENT ON COLUMN speakers.politician_id IS 'Reference to the politician this speaker represents. Multiple speakers can point to the same politician.';

-- Add additional columns to politicians table that were in init.sql but missing from entities
ALTER TABLE politicians ADD COLUMN IF NOT EXISTS furigana VARCHAR;
ALTER TABLE politicians ADD COLUMN IF NOT EXISTS district VARCHAR;
ALTER TABLE politicians ADD COLUMN IF NOT EXISTS profile_page_url VARCHAR;

COMMENT ON COLUMN politicians.furigana IS 'Name reading in hiragana';
COMMENT ON COLUMN politicians.district IS 'Electoral district';
COMMENT ON COLUMN politicians.profile_page_url IS 'URL to profile page on party or government website';
