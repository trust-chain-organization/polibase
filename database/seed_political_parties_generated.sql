-- Generated from database on 2025-07-12 02:28:05
-- political_parties seed data

INSERT INTO political_parties (name, members_list_url) VALUES
('NHK党', NULL),
('その他', NULL),
('みんなの党', NULL),
('れいわ新選組', NULL),
('公明党', NULL),
('参政党', NULL),
('国民民主党', NULL),
('大阪維新の会', NULL),
('日本共産党', NULL),
('日本維新の会', NULL),
('減税日本', NULL),
('無所属', NULL),
('社会民主党', NULL),
('立憲民主党', NULL),
('自由民主党', NULL),
('諸派', NULL),
('都民ファーストの会', NULL)
ON CONFLICT (name) DO NOTHING;
