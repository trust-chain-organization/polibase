-- Remove position column from extracted_politicians and politicians tables
-- Position information should be represented through politician_affiliations with conferences

-- Drop position column from extracted_politicians table
ALTER TABLE extracted_politicians
DROP COLUMN IF EXISTS position;

-- Drop position column from politicians table
ALTER TABLE politicians
DROP COLUMN IF EXISTS position;

-- Note: This is a destructive change that will permanently remove the position data
-- Position information should be managed through politician_affiliations table instead
