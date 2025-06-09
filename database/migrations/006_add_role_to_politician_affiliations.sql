-- Add role column to politician_affiliations table
ALTER TABLE politician_affiliations
ADD COLUMN role VARCHAR(100);

-- Add comment to explain the column purpose
COMMENT ON COLUMN politician_affiliations.role IS '議員の役職（例：議長、副議長、委員長、委員など）';