-- 議案への会派単位の賛否情報テーブル
-- 会派（議員団）が議案に対してどのような判断をしたかを記録
CREATE TABLE IF NOT EXISTS proposal_parliamentary_group_judges (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id),
    parliamentary_group_id INTEGER NOT NULL REFERENCES parliamentary_groups(id),
    judgment VARCHAR(50) NOT NULL, -- 賛成/反対/棄権/欠席
    member_count INTEGER, -- この判断をした会派メンバーの人数
    note TEXT, -- 備考（例：「自由投票」「一部反対」など）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 同一議案・会派の重複を防ぐ
    UNIQUE(proposal_id, parliamentary_group_id)
);

-- インデックスの作成
CREATE INDEX idx_proposal_parliamentary_group_judges_proposal
    ON proposal_parliamentary_group_judges(proposal_id);
CREATE INDEX idx_proposal_parliamentary_group_judges_group
    ON proposal_parliamentary_group_judges(parliamentary_group_id);
CREATE INDEX idx_proposal_parliamentary_group_judges_judgment
    ON proposal_parliamentary_group_judges(judgment);

-- コメント追加
COMMENT ON TABLE proposal_parliamentary_group_judges IS '議案への会派単位の賛否情報';
COMMENT ON COLUMN proposal_parliamentary_group_judges.proposal_id IS '議案ID';
COMMENT ON COLUMN proposal_parliamentary_group_judges.parliamentary_group_id IS '会派ID';
COMMENT ON COLUMN proposal_parliamentary_group_judges.judgment IS '賛否判断（賛成/反対/棄権/欠席）';
COMMENT ON COLUMN proposal_parliamentary_group_judges.member_count IS 'この判断をした会派メンバーの人数';
COMMENT ON COLUMN proposal_parliamentary_group_judges.note IS '備考（自由投票など特記事項）';
