-- Migration: Remove foreign key constraint between conferences and governing_bodies
-- This allows conferences to exist without a governing body

-- Drop foreign key constraint
ALTER TABLE conferences
DROP CONSTRAINT IF EXISTS conferences_governing_body_id_fkey;

-- Allow NULL values for governing_body_id
ALTER TABLE conferences
ALTER COLUMN governing_body_id DROP NOT NULL;

-- Add comment explaining the change
COMMENT ON COLUMN conferences.governing_body_id IS 'Optional reference to governing body. NULL means the conference is not associated with any governing body.';
