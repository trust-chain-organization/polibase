-- 議員団テーブルの作成
CREATE TABLE parliamentary_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    conference_id INT NOT NULL REFERENCES conferences(id),
    url VARCHAR(500),
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, conference_id)
);

-- 議員団名と会議体IDの複合インデックス
CREATE INDEX idx_parliamentary_groups_name_conference ON parliamentary_groups(name, conference_id);

-- 議員団所属履歴テーブルの作成
CREATE TABLE parliamentary_group_memberships (
    id SERIAL PRIMARY KEY,
    politician_id INT NOT NULL REFERENCES politicians(id),
    parliamentary_group_id INT NOT NULL REFERENCES parliamentary_groups(id),
    start_date DATE NOT NULL,
    end_date DATE,
    role VARCHAR(100), -- 団長、幹事長、政調会長など
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_end_date_after_start CHECK (end_date IS NULL OR end_date >= start_date)
);

-- インデックスの作成
CREATE INDEX idx_parliamentary_group_memberships_politician ON parliamentary_group_memberships(politician_id);
CREATE INDEX idx_parliamentary_group_memberships_group ON parliamentary_group_memberships(parliamentary_group_id);
CREATE INDEX idx_parliamentary_group_memberships_dates ON parliamentary_group_memberships(start_date, end_date);

-- 議案賛否テーブルに議員団IDを追加
ALTER TABLE proposal_judges
ADD COLUMN parliamentary_group_id INT REFERENCES parliamentary_groups(id);

-- 議員団IDのインデックスを追加
CREATE INDEX idx_proposal_judges_parliamentary_group ON proposal_judges(parliamentary_group_id);

-- 更新日時の自動更新トリガー関数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- parliamentary_groupsテーブルのトリガー
CREATE TRIGGER update_parliamentary_groups_updated_at BEFORE UPDATE
    ON parliamentary_groups FOR EACH ROW EXECUTE FUNCTION
    update_updated_at_column();

-- parliamentary_group_membershipsテーブルのトリガー
CREATE TRIGGER update_parliamentary_group_memberships_updated_at BEFORE UPDATE
    ON parliamentary_group_memberships FOR EACH ROW EXECUTE FUNCTION
    update_updated_at_column();

-- コメント追加
COMMENT ON TABLE parliamentary_groups IS '議員団（会派）';
COMMENT ON COLUMN parliamentary_groups.name IS '議員団名';
COMMENT ON COLUMN parliamentary_groups.conference_id IS '所属する会議体ID';
COMMENT ON COLUMN parliamentary_groups.url IS '議員団の公式URL';
COMMENT ON COLUMN parliamentary_groups.description IS '議員団の説明';
COMMENT ON COLUMN parliamentary_groups.is_active IS '現在活動中かどうか';

COMMENT ON TABLE parliamentary_group_memberships IS '議員団所属履歴';
COMMENT ON COLUMN parliamentary_group_memberships.politician_id IS '政治家ID';
COMMENT ON COLUMN parliamentary_group_memberships.parliamentary_group_id IS '議員団ID';
COMMENT ON COLUMN parliamentary_group_memberships.start_date IS '所属開始日';
COMMENT ON COLUMN parliamentary_group_memberships.end_date IS '所属終了日（現在所属中の場合はNULL）';
COMMENT ON COLUMN parliamentary_group_memberships.role IS '議員団内での役職';

COMMENT ON COLUMN proposal_judges.parliamentary_group_id IS '賛否投票時の所属議員団ID';
