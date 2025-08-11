-- Add created_by column to llm_processing_history table
ALTER TABLE llm_processing_history
ADD COLUMN created_by VARCHAR(100) DEFAULT 'system';

-- Add comment for the new column
COMMENT ON COLUMN llm_processing_history.created_by IS '処理を開始したユーザーまたはシステム';

-- Create index for created_by column for filtering
CREATE INDEX idx_llm_history_created_by ON llm_processing_history(created_by);
