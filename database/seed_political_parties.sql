-- Seed data for political_parties table
-- 政党のマスターデータ

INSERT INTO political_parties (name) VALUES
-- 主要政党
('自由民主党'),
('立憲民主党'),
('公明党'),
('日本維新の会'),
('国民民主党'),
('日本共産党'),
('れいわ新選組'),
('社会民主党'),
('NHK党'),
('参政党'),

-- 地域政党
('都民ファーストの会'),
('大阪維新の会'),
('減税日本'),
('みんなの党'),

-- 無所属・その他
('無所属'),
('諸派'),
('その他')

ON CONFLICT (name) DO NOTHING;
