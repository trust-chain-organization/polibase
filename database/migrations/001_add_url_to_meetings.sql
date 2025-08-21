-- Migration: Add URL column to meetings table
-- Date: 2025-06-02
-- Issue: #47 - Add URL field to meetings schema

-- Add URL column to meetings table if it doesn't exist
ALTER TABLE meetings ADD COLUMN IF NOT EXISTS url VARCHAR;

-- Add comment to the column
COMMENT ON COLUMN meetings.url IS '会議関連のURLまたは議事録PDFのURL';
