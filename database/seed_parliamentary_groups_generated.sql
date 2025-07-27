-- Generated from database on 2025-07-27 09:34:36
-- parliamentary_groups seed data

INSERT INTO parliamentary_groups (name, conference_id, url, description, is_active) VALUES
-- 京都府京都市 - 京都市議会
(' 日本共産党京都市会議員団', (SELECT c.id FROM conferences c JOIN governing_bodies gb ON c.governing_body_id = gb.id WHERE c.name = '京都市議会' AND gb.name = '京都府京都市' AND gb.type = '市町村'), 'https://cpgkyoto.jp/', NULL, true),
('公明党京都市会議員団', (SELECT c.id FROM conferences c JOIN governing_bodies gb ON c.governing_body_id = gb.id WHERE c.name = '京都市議会' AND gb.name = '京都府京都市' AND gb.type = '市町村'), 'https://www.komeito-kyotocity.com/#member', NULL, true),
('改新京都', (SELECT c.id FROM conferences c JOIN governing_bodies gb ON c.governing_body_id = gb.id WHERE c.name = '京都市議会' AND gb.name = '京都府京都市' AND gb.type = '市町村'), 'https://www2.city.kyoto.lg.jp/shikai/meibo/kaiha/kaishinkyoto.html', NULL, true),
('民主・市民フォーラム京都市会議員団', (SELECT c.id FROM conferences c JOIN governing_bodies gb ON c.governing_body_id = gb.id WHERE c.name = '京都市議会' AND gb.name = '京都府京都市' AND gb.type = '市町村'), 'https://www2.city.kyoto.lg.jp/shikai/meibo/kaiha/minsyu-kyoto.html', NULL, true),
('無所属', (SELECT c.id FROM conferences c JOIN governing_bodies gb ON c.governing_body_id = gb.id WHERE c.name = '京都市議会' AND gb.name = '京都府京都市' AND gb.type = '市町村'), 'https://www2.city.kyoto.lg.jp/shikai/meibo/kaiha/mushozoku.html', NULL, true),
('維新・京都・国民市会議員団', (SELECT c.id FROM conferences c JOIN governing_bodies gb ON c.governing_body_id = gb.id WHERE c.name = '京都市議会' AND gb.name = '京都府京都市' AND gb.type = '市町村'), 'https://www2.city.kyoto.lg.jp/shikai/meibo/kaiha/ishin-kyoto-kokumin.html', NULL, true),
('自由民主党京都市会議員団', (SELECT c.id FROM conferences c JOIN governing_bodies gb ON c.governing_body_id = gb.id WHERE c.name = '京都市議会' AND gb.name = '京都府京都市' AND gb.type = '市町村'), 'https://jimin-kyoto.jp/member_list/', NULL, true)
ON CONFLICT (name, conference_id) DO NOTHING;
