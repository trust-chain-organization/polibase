-- Add process_id column to minutes table to link with LLM processing history
ALTER TABLE minutes ADD COLUMN llm_process_id VARCHAR(100);

-- Create index for efficient querying
CREATE INDEX idx_minutes_llm_process_id ON minutes(llm_process_id);

-- Add comment
COMMENT ON COLUMN minutes.llm_process_id IS 'LLM処理履歴との関連付けID';
