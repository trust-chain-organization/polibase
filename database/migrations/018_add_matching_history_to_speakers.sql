-- Add matching_process_id column to speakers table for tracking LLM matching history
ALTER TABLE speakers
    ADD COLUMN IF NOT EXISTS matching_process_id INTEGER,
    ADD COLUMN IF NOT EXISTS matching_confidence DECIMAL(3,2),
    ADD COLUMN IF NOT EXISTS matching_reason TEXT;

-- Add foreign key constraint to llm_processing_history table
ALTER TABLE speakers
    ADD CONSTRAINT fk_speakers_matching_process
    FOREIGN KEY (matching_process_id)
    REFERENCES llm_processing_history(id)
    ON DELETE SET NULL;

-- Create index for matching_process_id
CREATE INDEX idx_speakers_matching_process_id ON speakers(matching_process_id);

-- Add comments
COMMENT ON COLUMN speakers.matching_process_id IS 'LLM処理履歴のID（speaker_matchingプロセス）';
COMMENT ON COLUMN speakers.matching_confidence IS 'マッチングの信頼度スコア (0.00-1.00)';
COMMENT ON COLUMN speakers.matching_reason IS 'マッチング判定の理由';
