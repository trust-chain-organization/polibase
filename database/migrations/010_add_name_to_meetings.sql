-- Add name column to meetings table for storing meeting names
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS name VARCHAR;