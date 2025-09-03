-- Create extracted_parliamentary_group_members table for staging scraped member data
CREATE TABLE extracted_parliamentary_group_members (
    id SERIAL PRIMARY KEY,
    parliamentary_group_id INTEGER NOT NULL REFERENCES parliamentary_groups(id),
    extracted_name VARCHAR(255) NOT NULL,
    extracted_role VARCHAR(100),
    extracted_party_name VARCHAR(255),
    extracted_district VARCHAR(255),
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
CREATE INDEX idx_extracted_parliamentary_group_members_group ON extracted_parliamentary_group_members(parliamentary_group_id);
CREATE INDEX idx_extracted_parliamentary_group_members_status ON extracted_parliamentary_group_members(matching_status);
CREATE INDEX idx_extracted_parliamentary_group_members_politician ON extracted_parliamentary_group_members(matched_politician_id);

-- Add comments
COMMENT ON TABLE extracted_parliamentary_group_members IS '議員団メンバー情報の抽出結果を保存する中間テーブル';
COMMENT ON COLUMN extracted_parliamentary_group_members.extracted_name IS 'Webページから抽出された議員名';
COMMENT ON COLUMN extracted_parliamentary_group_members.extracted_role IS '抽出された役職（団長、幹事長、政調会長など）';
COMMENT ON COLUMN extracted_parliamentary_group_members.extracted_party_name IS '抽出された所属政党名';
COMMENT ON COLUMN extracted_parliamentary_group_members.extracted_district IS '抽出された選挙区';
COMMENT ON COLUMN extracted_parliamentary_group_members.matched_politician_id IS 'マッチングされた政治家ID';
COMMENT ON COLUMN extracted_parliamentary_group_members.matching_confidence IS 'マッチングの信頼度（0-1）';
COMMENT ON COLUMN extracted_parliamentary_group_members.matching_status IS 'マッチング状態（pending:未処理, matched:マッチ済, no_match:該当なし, needs_review:要確認）';
