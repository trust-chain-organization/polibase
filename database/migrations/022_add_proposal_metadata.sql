-- 議案テーブルにメタデータカラムを追加
ALTER TABLE proposals
ADD COLUMN url VARCHAR,                    -- 議案の原文URL
ADD COLUMN submission_date DATE,           -- 提出日
ADD COLUMN submitter VARCHAR,              -- 提出者
ADD COLUMN proposal_number VARCHAR,        -- 議案番号
ADD COLUMN meeting_id INTEGER REFERENCES meetings(id),  -- 関連する会議
ADD COLUMN summary TEXT;                   -- 議案概要

-- メタデータカラムにコメントを追加
COMMENT ON COLUMN proposals.url IS '議案の原文URL';
COMMENT ON COLUMN proposals.submission_date IS '議案の提出日';
COMMENT ON COLUMN proposals.submitter IS '議案の提出者（議員名、委員会名など）';
COMMENT ON COLUMN proposals.proposal_number IS '議案番号（例: 議案第1号）';
COMMENT ON COLUMN proposals.meeting_id IS '議案が提出・審議された会議のID';
COMMENT ON COLUMN proposals.summary IS '議案の概要説明';

-- インデックスの追加（検索性能向上のため）
CREATE INDEX idx_proposals_submission_date ON proposals(submission_date);
CREATE INDEX idx_proposals_meeting ON proposals(meeting_id);
CREATE INDEX idx_proposals_proposal_number ON proposals(proposal_number);
