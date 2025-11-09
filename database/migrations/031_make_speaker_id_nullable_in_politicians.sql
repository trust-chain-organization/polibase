-- Make speaker_id nullable in politicians table
-- This allows creating politicians from extracted_politicians without requiring a speaker

-- Drop the UNIQUE constraint first
-- ALTER TABLE politicians DROP CONSTRAINT IF EXISTS politicians_speaker_id_key;
-- Note: speaker_id column was removed from politicians table in migration 032

-- Make speaker_id nullable
-- ALTER TABLE politicians ALTER COLUMN speaker_id DROP NOT NULL;
-- Note: speaker_id column was removed from politicians table in migration 032

-- Add comment to clarify the field's purpose
-- COMMENT ON COLUMN politicians.speaker_id IS 'Link to speaker when politician is identified from meeting minutes. NULL for politicians created from party websites.';
-- Note: speaker_id column was removed from politicians table in migration 032
