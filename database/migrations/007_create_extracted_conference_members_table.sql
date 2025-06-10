-- Create extracted_conference_members table for staging scraped member data
CREATE TABLE extracted_conference_members (
    id SERIAL PRIMARY KEY,
    conference_id INTEGER NOT NULL REFERENCES conferences(id),
    extracted_name VARCHAR(255) NOT NULL,
    extracted_role VARCHAR(100),
    extracted_party_name VARCHAR(255),
    source_url VARCHAR(500) NOT NULL,
    extracted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Matching results
    matched_politician_id INTEGER REFERENCES politicians(id),
    matching_confidence DECIMAL(3,2), -- 0.00 to 1.00
    matching_status VARCHAR(50) DEFAULT 'pending', -- pending, matched, no_match, needs_review
    matched_at TIMESTAMP,

    -- Additional extracted data
    additional_info TEXT,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX idx_extracted_conference_members_conference ON extracted_conference_members(conference_id);
CREATE INDEX idx_extracted_conference_members_status ON extracted_conference_members(matching_status);
CREATE INDEX idx_extracted_conference_members_politician ON extracted_conference_members(matched_politician_id);

-- Add comments
COMMENT ON TABLE extracted_conference_members IS '議会メンバー情報の抽出結果を保存する中間テーブル';
COMMENT ON COLUMN extracted_conference_members.extracted_name IS 'Webページから抽出された議員名';
COMMENT ON COLUMN extracted_conference_members.extracted_role IS '抽出された役職（議長、副議長、委員長など）';
COMMENT ON COLUMN extracted_conference_members.extracted_party_name IS '抽出された所属政党名';
COMMENT ON COLUMN extracted_conference_members.matched_politician_id IS 'マッチングされた政治家ID';
COMMENT ON COLUMN extracted_conference_members.matching_confidence IS 'マッチングの信頼度（0-1）';
COMMENT ON COLUMN extracted_conference_members.matching_status IS 'マッチング状態（pending:未処理, matched:マッチ済, no_match:該当なし, needs_review:要確認）';
