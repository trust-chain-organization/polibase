-- Create extracted_proposal_judges table for staging extracted proposal judgment data
CREATE TABLE extracted_proposal_judges (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id),

    -- Extracted data
    extracted_politician_name VARCHAR(255),
    extracted_party_name VARCHAR(255),
    extracted_parliamentary_group_name VARCHAR(255),
    extracted_judgment VARCHAR(50), -- 賛成/反対/棄権/欠席
    source_url VARCHAR(500),
    extracted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Matching results
    matched_politician_id INTEGER REFERENCES politicians(id),
    matched_parliamentary_group_id INTEGER REFERENCES parliamentary_groups(id),
    matching_confidence DECIMAL(3,2), -- 0.00 to 1.00
    matching_status VARCHAR(50) DEFAULT 'pending', -- pending, matched, no_match, needs_review
    matched_at TIMESTAMP,

    -- Additional data
    additional_data JSONB,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX idx_extracted_proposal_judges_proposal ON extracted_proposal_judges(proposal_id);
CREATE INDEX idx_extracted_proposal_judges_status ON extracted_proposal_judges(matching_status);
CREATE INDEX idx_extracted_proposal_judges_politician ON extracted_proposal_judges(matched_politician_id);
CREATE INDEX idx_extracted_proposal_judges_group ON extracted_proposal_judges(matched_parliamentary_group_id);
CREATE INDEX idx_extracted_proposal_judges_judgment ON extracted_proposal_judges(extracted_judgment);

-- Add comments
COMMENT ON TABLE extracted_proposal_judges IS '議案賛否情報の抽出結果を保存する中間テーブル';
COMMENT ON COLUMN extracted_proposal_judges.proposal_id IS '対象議案ID';
COMMENT ON COLUMN extracted_proposal_judges.extracted_politician_name IS 'Webページから抽出された議員名';
COMMENT ON COLUMN extracted_proposal_judges.extracted_party_name IS '抽出された所属政党名';
COMMENT ON COLUMN extracted_proposal_judges.extracted_parliamentary_group_name IS '抽出された議員団名';
COMMENT ON COLUMN extracted_proposal_judges.extracted_judgment IS '抽出された賛否情報（賛成/反対/棄権/欠席）';
COMMENT ON COLUMN extracted_proposal_judges.source_url IS '情報源のURL';
COMMENT ON COLUMN extracted_proposal_judges.matched_politician_id IS 'マッチングされた政治家ID';
COMMENT ON COLUMN extracted_proposal_judges.matched_parliamentary_group_id IS 'マッチングされた議員団ID';
COMMENT ON COLUMN extracted_proposal_judges.matching_confidence IS 'マッチングの信頼度（0-1）';
COMMENT ON COLUMN extracted_proposal_judges.matching_status IS 'マッチング状態（pending:未処理, matched:マッチ済, no_match:該当なし, needs_review:要確認）';
COMMENT ON COLUMN extracted_proposal_judges.additional_data IS '追加の抽出データ（JSON形式）';
