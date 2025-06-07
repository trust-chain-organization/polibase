-- Add additional columns to politicians table for party member scraping
ALTER TABLE politicians
ADD COLUMN IF NOT EXISTS position TEXT,
ADD COLUMN IF NOT EXISTS prefecture VARCHAR(10),
ADD COLUMN IF NOT EXISTS electoral_district TEXT,
ADD COLUMN IF NOT EXISTS profile_url TEXT;

-- Make speaker_id nullable temporarily to allow insertion without speaker
ALTER TABLE politicians
ALTER COLUMN speaker_id DROP NOT NULL;

-- Add comments
COMMENT ON COLUMN politicians.position IS '役職（衆議院議員、参議院議員など）';
COMMENT ON COLUMN politicians.prefecture IS '都道府県';
COMMENT ON COLUMN politicians.electoral_district IS '選挙区';
COMMENT ON COLUMN politicians.profile_url IS 'プロフィールページURL';
