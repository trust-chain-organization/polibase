-- Add attendees_mapping column to meetings table
-- This column stores the mapping between roles and names extracted from meeting minutes
-- Format: JSON object like {"議長": "西村義直", "委員長": "田中太郎"}

ALTER TABLE meetings
ADD COLUMN IF NOT EXISTS attendees_mapping JSONB;

-- Add comment to the column
COMMENT ON COLUMN meetings.attendees_mapping IS '出席者の役職と名前のマッピング (例: {"議長": "西村義直", "委員長": "田中太郎"})';
