-- Add 'converted' as a valid status for extracted_politicians table

-- Drop the existing check constraint
ALTER TABLE extracted_politicians DROP CONSTRAINT IF EXISTS check_status;

-- Add the new check constraint with 'converted' status
ALTER TABLE extracted_politicians
ADD CONSTRAINT check_status CHECK (
    status IN ('pending', 'reviewed', 'approved', 'rejected', 'converted')
);
