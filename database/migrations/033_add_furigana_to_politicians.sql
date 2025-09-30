-- Add furigana column to politicians table
-- This allows storing phonetic readings of politician names

ALTER TABLE politicians ADD COLUMN IF NOT EXISTS furigana VARCHAR(255);

-- Create index for furigana searches
CREATE INDEX IF NOT EXISTS idx_politicians_furigana ON politicians(furigana);

COMMENT ON COLUMN politicians.furigana IS '政治家名のふりがな（カタカナ）';
