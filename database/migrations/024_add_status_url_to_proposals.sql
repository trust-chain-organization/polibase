-- 議案テーブルのURL管理を詳細URLとステータスURLに分離

-- 1. 新しいカラムを追加
ALTER TABLE proposals
ADD COLUMN detail_url VARCHAR,
ADD COLUMN status_url VARCHAR;

-- 2. 既存データの移行（既存のurlをdetail_urlへ）
UPDATE proposals
SET detail_url = url
WHERE url IS NOT NULL;

-- 3. 古いurlカラムを削除
ALTER TABLE proposals
DROP COLUMN url;

-- 4. カラムにコメントを追加
COMMENT ON COLUMN proposals.detail_url IS '議案の詳細本文URL（法案内容、議案内容など）';
COMMENT ON COLUMN proposals.status_url IS '議案の審議状況URL（経過状態、賛成会派情報など）';

-- 5. インデックスの追加（検索性能向上のため）
CREATE INDEX idx_proposals_detail_url ON proposals(detail_url);
CREATE INDEX idx_proposals_status_url ON proposals(status_url);
