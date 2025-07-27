-- Generated from database on 2025-07-27 09:46:11
-- politicians seed data

INSERT INTO politicians (name, political_party_id, position, prefecture, electoral_district, profile_url) VALUES
-- 立憲民主党
('佐藤花子', (SELECT id FROM political_parties WHERE name = '立憲民主党'), '参議院議員', '大阪府', '大阪府', 'https://example.com/sato'),

-- 自由民主党
('山田太郎', (SELECT id FROM political_parties WHERE name = '自由民主党'), '衆議院議員', '東京都', '東京1区', 'https://example.com/yamada'),

-- 無所属
('鈴木一郎', NULL, '衆議院議員', '北海道', '北海道1区', 'https://example.com/suzuki')
;
