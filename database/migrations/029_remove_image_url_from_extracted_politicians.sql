-- Remove image_url column from extracted_politicians table
-- This column is not needed as we don't use politician images in the application

-- Drop the column
ALTER TABLE extracted_politicians
DROP COLUMN IF EXISTS image_url;

-- Note: This is a destructive change that will permanently remove the image_url data
-- Make sure to backup the database before running this migration if needed
