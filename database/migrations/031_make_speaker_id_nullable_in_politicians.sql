-- Make speaker_id nullable in politicians table
-- This allows creating politicians from extracted_politicians without requiring a speaker

-- Drop the UNIQUE constraint first
ALTER TABLE politicians DROP CONSTRAINT IF EXISTS politicians_speaker_id_key;

-- Make speaker_id nullable
ALTER TABLE politicians ALTER COLUMN speaker_id DROP NOT NULL;

-- Add comment to clarify the field's purpose
COMMENT ON COLUMN politicians.speaker_id IS 'Link to speaker when politician is identified from meeting minutes. NULL for politicians created from party websites.';
