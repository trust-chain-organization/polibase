-- Seed data for conferences table
-- 会議体（議会・委員会）のマスターデータ

INSERT INTO conferences (name, type, governing_body_id) VALUES
-- 国レベルの会議体（日本国 = ID 1と仮定）
('国会', '国会全体', 1),
('衆議院', '議院', 1),
('参議院', '議院', 1),

-- 衆議院の委員会
('衆議院本会議', '本会議', 1),
('衆議院内閣委員会', '常任委員会', 1),
('衆議院総務委員会', '常任委員会', 1),
('衆議院法務委員会', '常任委員会', 1),
('衆議院外務委員会', '常任委員会', 1),
('衆議院財務金融委員会', '常任委員会', 1),
('衆議院文部科学委員会', '常任委員会', 1),
('衆議院厚生労働委員会', '常任委員会', 1),
('衆議院農林水産委員会', '常任委員会', 1),
('衆議院経済産業委員会', '常任委員会', 1),
('衆議院国土交通委員会', '常任委員会', 1),
('衆議院環境委員会', '常任委員会', 1),
('衆議院安全保障委員会', '常任委員会', 1),
('衆議院予算委員会', '常任委員会', 1),
('衆議院決算行政監視委員会', '常任委員会', 1),
('衆議院議院運営委員会', '常任委員会', 1),
('衆議院懲罰委員会', '常任委員会', 1),

-- 参議院の委員会
('参議院本会議', '本会議', 1),
('参議院内閣委員会', '常任委員会', 1),
('参議院総務委員会', '常任委員会', 1),
('参議院法務委員会', '常任委員会', 1),
('参議院外交防衛委員会', '常任委員会', 1),
('参議院財政金融委員会', '常任委員会', 1),
('参議院文教科学委員会', '常任委員会', 1),
('参議院厚生労働委員会', '常任委員会', 1),
('参議院農林水産委員会', '常任委員会', 1),
('参議院経済産業委員会', '常任委員会', 1),
('参議院国土交通委員会', '常任委員会', 1),
('参議院環境委員会', '常任委員会', 1),
('参議院予算委員会', '常任委員会', 1),
('参議院決算委員会', '常任委員会', 1),
('参議院行政監視委員会', '常任委員会', 1),
('参議院議院運営委員会', '常任委員会', 1),
('参議院懲罰委員会', '常任委員会', 1),

-- 両院合同委員会等
('国会合同審査会', '合同委員会', 1),
('国政調査特別委員会', '特別委員会', 1),

-- 都道府県議会（主要都府県の例）
-- 注意: governing_body_idは実際のIDに置き換える必要があります
('北海道議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '北海道' AND type = '都道府県')),
('東京都議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '東京都' AND type = '都道府県')),
('神奈川県議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '神奈川県' AND type = '都道府県')),
('大阪府議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '大阪府' AND type = '都道府県')),
('愛知県議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '愛知県' AND type = '都道府県')),
('埼玉県議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '埼玉県' AND type = '都道府県')),
('千葉県議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '千葉県' AND type = '都道府県')),
('兵庫県議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '兵庫県' AND type = '都道府県')),
('福岡県議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '福岡県' AND type = '都道府県')),
('静岡県議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '静岡県' AND type = '都道府県')),

-- 政令指定都市議会
('札幌市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '札幌市' AND type = '市町村')),
('仙台市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '仙台市' AND type = '市町村')),
('さいたま市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = 'さいたま市' AND type = '市町村')),
('千葉市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '千葉市' AND type = '市町村')),
('横浜市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '横浜市' AND type = '市町村')),
('川崎市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '川崎市' AND type = '市町村')),
('相模原市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '相模原市' AND type = '市町村')),
('新潟市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '新潟市' AND type = '市町村')),
('静岡市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '静岡市' AND type = '市町村')),
('浜松市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '浜松市' AND type = '市町村')),
('名古屋市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '名古屋市' AND type = '市町村')),
('京都市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '京都市' AND type = '市町村')),
('大阪市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '大阪市' AND type = '市町村')),
('堺市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '堺市' AND type = '市町村')),
('神戸市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '神戸市' AND type = '市町村')),
('岡山市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '岡山市' AND type = '市町村')),
('広島市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '広島市' AND type = '市町村')),
('北九州市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '北九州市' AND type = '市町村')),
('福岡市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '福岡市' AND type = '市町村')),
('熊本市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '熊本市' AND type = '市町村')),

-- 東京23区議会
('千代田区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '千代田区' AND type = '市町村')),
('中央区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '中央区' AND type = '市町村')),
('港区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '港区' AND type = '市町村')),
('新宿区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '新宿区' AND type = '市町村')),
('文京区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '文京区' AND type = '市町村')),
('台東区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '台東区' AND type = '市町村')),
('墨田区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '墨田区' AND type = '市町村')),
('江東区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '江東区' AND type = '市町村')),
('品川区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '品川区' AND type = '市町村')),
('目黒区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '目黒区' AND type = '市町村')),
('大田区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '大田区' AND type = '市町村')),
('世田谷区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '世田谷区' AND type = '市町村')),
('渋谷区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '渋谷区' AND type = '市町村')),
('中野区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '中野区' AND type = '市町村')),
('杉並区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '杉並区' AND type = '市町村')),
('豊島区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '豊島区' AND type = '市町村')),
('北区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '北区' AND type = '市町村')),
('荒川区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '荒川区' AND type = '市町村')),
('板橋区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '板橋区' AND type = '市町村')),
('練馬区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '練馬区' AND type = '市町村')),
('足立区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '足立区' AND type = '市町村')),
('葛飾区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '葛飾区' AND type = '市町村')),
('江戸川区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '江戸川区' AND type = '市町村'))

-- 注意: governing_body_idはSUBQUERYで動的に取得していますが、
-- パフォーマンスを考慮して実際のIDハードコーディングも検討してください

ON CONFLICT (name, governing_body_id) DO NOTHING;
