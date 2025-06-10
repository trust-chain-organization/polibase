-- Add role column to politician_affiliations table
ALTER TABLE politician_affiliations
ADD COLUMN role VARCHAR(100);

-- Add comment
COMMENT ON COLUMN politician_affiliations.role IS '会議体での役職（議長、副議長、委員長、副委員長、理事、委員など）';

-- Create index for role
CREATE INDEX idx_politician_affiliations_role ON politician_affiliations(role);
