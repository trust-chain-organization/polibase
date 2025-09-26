-- Create extracted_politicians table for storing LLM-extracted politician data before review
CREATE TABLE IF NOT EXISTS extracted_politicians (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    party_id INTEGER REFERENCES political_parties(id),
    district TEXT,
    position TEXT,
    profile_url TEXT,
    image_url TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    extracted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    reviewer_id INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_status CHECK (status IN ('pending', 'reviewed', 'approved', 'rejected'))
);

-- Add comments for documentation
COMMENT ON TABLE extracted_politicians IS 'LLMが抽出した政治家データの中間テーブル（レビュー前）';
COMMENT ON COLUMN extracted_politicians.name IS '政治家名';
COMMENT ON COLUMN extracted_politicians.party_id IS '政党ID（political_partiesテーブルへの参照）';
COMMENT ON COLUMN extracted_politicians.district IS '選挙区';
COMMENT ON COLUMN extracted_politicians.position IS '役職（衆議院議員、参議院議員など）';
COMMENT ON COLUMN extracted_politicians.profile_url IS 'プロフィールページURL';
COMMENT ON COLUMN extracted_politicians.image_url IS 'プロフィール画像URL';
COMMENT ON COLUMN extracted_politicians.status IS 'レビューステータス（pending: 未レビュー, reviewed: レビュー済み, approved: 承認, rejected: 却下）';
COMMENT ON COLUMN extracted_politicians.extracted_at IS 'LLMによる抽出日時';
COMMENT ON COLUMN extracted_politicians.reviewed_at IS 'レビュー実施日時';
COMMENT ON COLUMN extracted_politicians.reviewer_id IS 'レビュー実施者ID';

-- Create indexes for better query performance
CREATE INDEX idx_extracted_politicians_party_id ON extracted_politicians(party_id);
CREATE INDEX idx_extracted_politicians_status ON extracted_politicians(status);
CREATE INDEX idx_extracted_politicians_extracted_at ON extracted_politicians(extracted_at DESC);
CREATE INDEX idx_extracted_politicians_name_party ON extracted_politicians(name, party_id);

-- Create trigger to auto-update updated_at column
CREATE TRIGGER update_extracted_politicians_updated_at
    BEFORE UPDATE ON extracted_politicians
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
