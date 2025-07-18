-- Create llm_processing_history table for tracking all LLM processing operations
CREATE TABLE llm_processing_history (
    id SERIAL PRIMARY KEY,

    -- Processing information
    processing_type VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,

    -- Prompt information
    prompt_template TEXT NOT NULL,
    prompt_variables JSONB NOT NULL DEFAULT '{}',

    -- Input reference
    input_reference_type VARCHAR(50) NOT NULL,
    input_reference_id INTEGER NOT NULL,

    -- Processing status and results
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    result JSONB,
    error_message TEXT,

    -- Additional metadata
    processing_metadata JSONB NOT NULL DEFAULT '{}',

    -- Timing information
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Standard timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX idx_llm_history_processing_type ON llm_processing_history(processing_type);
CREATE INDEX idx_llm_history_model ON llm_processing_history(model_name, model_version);
CREATE INDEX idx_llm_history_status ON llm_processing_history(status);
CREATE INDEX idx_llm_history_input_ref ON llm_processing_history(input_reference_type, input_reference_id);
CREATE INDEX idx_llm_history_created_at ON llm_processing_history(created_at);
CREATE INDEX idx_llm_history_started_at ON llm_processing_history(started_at);

-- Add comments
COMMENT ON TABLE llm_processing_history IS 'LLM処理の履歴を記録するテーブル';
COMMENT ON COLUMN llm_processing_history.processing_type IS '処理タイプ（minutes_division, speaker_matching等）';
COMMENT ON COLUMN llm_processing_history.model_name IS '使用したLLMモデル名（例：gemini-2.0-flash）';
COMMENT ON COLUMN llm_processing_history.model_version IS 'モデルのバージョン';
COMMENT ON COLUMN llm_processing_history.prompt_template IS '使用したプロンプトテンプレート';
COMMENT ON COLUMN llm_processing_history.prompt_variables IS 'プロンプトに代入された変数のJSON';
COMMENT ON COLUMN llm_processing_history.input_reference_type IS '処理対象のエンティティタイプ（meeting, speaker等）';
COMMENT ON COLUMN llm_processing_history.input_reference_id IS '処理対象のエンティティID';
COMMENT ON COLUMN llm_processing_history.status IS '処理ステータス（pending, in_progress, completed, failed）';
COMMENT ON COLUMN llm_processing_history.result IS '処理結果のJSON';
COMMENT ON COLUMN llm_processing_history.error_message IS 'エラーメッセージ（失敗時）';
COMMENT ON COLUMN llm_processing_history.processing_metadata IS '追加のメタデータ（トークン数、レスポンス時間等）';
COMMENT ON COLUMN llm_processing_history.started_at IS '処理開始時刻';
COMMENT ON COLUMN llm_processing_history.completed_at IS '処理完了時刻';

-- Add trigger to update updated_at
CREATE OR REPLACE FUNCTION update_llm_processing_history_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_llm_processing_history_updated_at
    BEFORE UPDATE ON llm_processing_history
    FOR EACH ROW
    EXECUTE FUNCTION update_llm_processing_history_updated_at();
