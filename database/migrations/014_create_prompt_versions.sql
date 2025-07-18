-- Create prompt_versions table for tracking prompt template versions
CREATE TABLE prompt_versions (
    id SERIAL PRIMARY KEY,

    -- Prompt identification
    prompt_key VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,

    -- Prompt content
    template TEXT NOT NULL,
    description TEXT,

    -- Status and metadata
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    variables TEXT[], -- Array of variable names expected in the template
    metadata JSONB NOT NULL DEFAULT '{}',
    created_by VARCHAR(100),

    -- Standard timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint to prevent duplicate versions
    CONSTRAINT uk_prompt_version UNIQUE (prompt_key, version)
);

-- Create indexes for efficient querying
CREATE INDEX idx_prompt_versions_key ON prompt_versions(prompt_key);
CREATE INDEX idx_prompt_versions_active ON prompt_versions(prompt_key, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_prompt_versions_created_at ON prompt_versions(created_at);

-- Add comments
COMMENT ON TABLE prompt_versions IS 'プロンプトテンプレートのバージョン管理テーブル';
COMMENT ON COLUMN prompt_versions.prompt_key IS 'プロンプトの識別キー（例：minutes_divide, speaker_match）';
COMMENT ON COLUMN prompt_versions.version IS 'バージョン番号（例：1.0.0, 2023-12-01-001）';
COMMENT ON COLUMN prompt_versions.template IS 'プロンプトテンプレートの内容';
COMMENT ON COLUMN prompt_versions.description IS 'このバージョンの説明';
COMMENT ON COLUMN prompt_versions.is_active IS '現在アクティブなバージョンかどうか';
COMMENT ON COLUMN prompt_versions.variables IS 'テンプレート内で使用される変数名のリスト';
COMMENT ON COLUMN prompt_versions.metadata IS '追加のメタデータ（パフォーマンス指標、使用上の注意など）';
COMMENT ON COLUMN prompt_versions.created_by IS 'このバージョンを作成したユーザーまたはシステム';

-- Add trigger to update updated_at
CREATE OR REPLACE FUNCTION update_prompt_versions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_prompt_versions_updated_at
    BEFORE UPDATE ON prompt_versions
    FOR EACH ROW
    EXECUTE FUNCTION update_prompt_versions_updated_at();

-- Function to ensure only one active version per prompt_key
CREATE OR REPLACE FUNCTION ensure_single_active_prompt_version()
RETURNS TRIGGER AS $$
BEGIN
    -- If setting this version as active, deactivate others
    IF NEW.is_active = TRUE THEN
        UPDATE prompt_versions
        SET is_active = FALSE
        WHERE prompt_key = NEW.prompt_key
          AND id != NEW.id
          AND is_active = TRUE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_ensure_single_active_prompt_version
    BEFORE INSERT OR UPDATE ON prompt_versions
    FOR EACH ROW
    WHEN (NEW.is_active = TRUE)
    EXECUTE FUNCTION ensure_single_active_prompt_version();
