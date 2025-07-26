-- 政治家テーブルに党内役職カラムを追加
-- 代表、幹事長、政調会長などの党内での役職を保存

ALTER TABLE politicians
ADD COLUMN party_position TEXT;

-- コメント追加
COMMENT ON COLUMN politicians.party_position IS '政党内での役職（代表、幹事長、政調会長など）';
