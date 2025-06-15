-- 議員団メンバー抽出結果を保存するステージングテーブル
CREATE TABLE IF NOT EXISTS extracted_parliamentary_group_members (
    id SERIAL PRIMARY KEY,
    parliamentary_group_id INTEGER NOT NULL REFERENCES parliamentary_groups(id) ON DELETE CASCADE,

    -- 抽出された情報
    extracted_name VARCHAR(255) NOT NULL,
    extracted_role VARCHAR(100),  -- 団長、幹事長など
    extracted_party_name VARCHAR(100),  -- 政党名（抽出できれば）
    extracted_electoral_district VARCHAR(100),  -- 選挙区（抽出できれば）
    extracted_profile_url VARCHAR(500),  -- プロフィールページURL（抽出できれば）

    -- マッチング情報
    matched_politician_id INTEGER REFERENCES politicians(id) ON DELETE SET NULL,
    matching_status VARCHAR(20) DEFAULT 'pending' CHECK (matching_status IN ('pending', 'matched', 'needs_review', 'no_match')),
    matching_confidence DECIMAL(3,2),  -- 0.00 - 1.00
    matching_notes TEXT,  -- マッチング時のメモ（複数候補がいた場合など）

    -- メタデータ
    extraction_date DATE NOT NULL DEFAULT CURRENT_DATE,
    source_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 同じ議員団から同じ名前の人を重複して抽出しないようにする
    UNIQUE(parliamentary_group_id, extracted_name)
);

-- インデックス
CREATE INDEX idx_extracted_pg_members_group_id ON extracted_parliamentary_group_members(parliamentary_group_id);
CREATE INDEX idx_extracted_pg_members_status ON extracted_parliamentary_group_members(matching_status);
CREATE INDEX idx_extracted_pg_members_politician ON extracted_parliamentary_group_members(matched_politician_id);

-- 更新時刻を自動更新するトリガー
CREATE TRIGGER update_extracted_pg_members_updated_at
    BEFORE UPDATE ON extracted_parliamentary_group_members
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
