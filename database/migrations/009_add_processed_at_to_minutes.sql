-- Add processed_at column to minutes table for tracking when minutes were processed
ALTER TABLE minutes ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP;

-- Create index for efficient queries on processed minutes
CREATE INDEX IF NOT EXISTS idx_minutes_processed_at ON minutes(processed_at);
