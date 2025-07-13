-- Generated from database on 2025-07-13 01:57:45
-- conferences seed data

INSERT INTO conferences (name, type, governing_body_id, members_introduction_url) VALUES
-- 日本国 (国)
('参議院', '議院', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/giin/217/giin.htm'),
('参議院予算委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0027.htm'),
('参議院内閣委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0063.htm'),
('参議院厚生労働委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0069.htm'),
('参議院国土交通委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0072.htm'),
('参議院外交防衛委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0066.htm'),
('参議院懲罰委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0031.htm'),
('参議院文教科学委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0068.htm'),
('参議院決算委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0028.htm'),
('参議院法務委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0065.htm'),
('参議院環境委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0073.htm'),
('参議院経済産業委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0071.htm'),
('参議院総務委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0064.htm'),
('参議院行政監視委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0061.htm'),
('参議院議院運営委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0029.htm'),
('参議院財政金融委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0067.htm'),
('参議院農林水産委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/konkokkai/current/list/l0070.htm'),
('衆議院', '議院', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_annai.nsf/html/statics/syu/1giin.htm'),
('衆議院予算委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0140.htm'),
('衆議院内閣委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0010.htm'),
('衆議院厚生労働委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0070.htm'),
('衆議院国土交通委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0100.htm'),
('衆議院外務委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0040.htm'),
('衆議院安全保障委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0120.htm'),
('衆議院懲罰委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0170.htm'),
('衆議院文部科学委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0060.htm'),
('衆議院決算行政監視委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0150.htm'),
('衆議院法務委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0030.htm'),
('衆議院環境委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0110.htm'),
('衆議院経済産業委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0090.htm'),
('衆議院総務委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0020.htm'),
('衆議院議院運営委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0160.htm'),
('衆議院財務金融委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0050.htm'),
('衆議院農林水産委員会', '常任委員会', (SELECT id FROM governing_bodies WHERE name = '日本国' AND type = '国'), 'https://www.shugiin.go.jp/internet/itdb_iinkai.nsf/html/iinkai/iin_j0080.htm'),

-- 兵庫県 (都道府県)
('兵庫県議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '兵庫県' AND type = '都道府県'), 'https://web.pref.hyogo.lg.jp/gikai/giinshokai/shokai/50on/50on_ichiran23.html'),

-- 北海道 (都道府県)
('北海道議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '北海道' AND type = '都道府県'), 'https://www.gikai.pref.hokkaido.lg.jp/meibo/pdf-index.html'),

-- 千葉県 (都道府県)
('千葉県議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '千葉県' AND type = '都道府県'), 'https://www.pref.chiba.lg.jp/gikai/giji/giin/giinshoukai/index.html'),

-- 埼玉県 (都道府県)
('埼玉県議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '埼玉県' AND type = '都道府県'), 'https://www.pref.saitama.lg.jp/e1601/gikai-member-50on.html'),

-- 大阪府 (都道府県)
('大阪府議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '大阪府' AND type = '都道府県'), 'https://www.pref.osaka.lg.jp/o170010/gikai_somu/sugatami20/index50.html'),

-- 愛知県 (都道府県)
('愛知県議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '愛知県' AND type = '都道府県'), 'https://www.pref.aichi.jp/gikai/syoukai/'),

-- 東京都 (都道府県)
('東京都議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '東京都' AND type = '都道府県'), 'https://www.gikai.metro.tokyo.lg.jp/membership/japanese-syllabary.html'),

-- 神奈川県 (都道府県)
('神奈川県議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '神奈川県' AND type = '都道府県'), 'https://www.pref.kanagawa.jp/gikai/p80005.html'),

-- 福岡県 (都道府県)
('福岡県議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '福岡県' AND type = '都道府県'), 'https://www.gikai.pref.fukuoka.lg.jp/site/giin/all.html'),

-- 静岡県 (都道府県)
('静岡県議会', '都道府県議会', (SELECT id FROM governing_bodies WHERE name = '静岡県' AND type = '都道府県'), 'https://www.pref.shizuoka.jp/kensei/kengikai/giinshokai/1068855/index.html'),

-- さいたま市 (市町村)
('さいたま市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = 'さいたま市' AND type = '市町村'), 'https://www.city.saitama.lg.jp/gikai/001/meibo/p005180.html'),

-- 世田谷区 (市町村)
('世田谷区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '世田谷区' AND type = '市町村'), 'https://www.city.setagaya.lg.jp/02030/9461.html'),

-- 中央区 (市町村)
('中央区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '中央区' AND type = '市町村'), 'https://www.kugikai.city.chuo.lg.jp/kugikai/meibo.html'),

-- 中野区 (市町村)
('中野区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '中野区' AND type = '市町村'), 'https://kugikai-nakano.jp/giin_list.html'),

-- 京都市 (市町村)
('京都市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '京都市' AND type = '市町村'), 'https://www2.city.kyoto.lg.jp/shikai/meibo/gojuon.html'),

-- 仙台市 (市町村)
('仙台市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '仙台市' AND type = '市町村'), 'https://www.gikai.city.sendai.jp/list/district/index.html'),

-- 北九州市 (市町村)
('北九州市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '北九州市' AND type = '市町村'), 'https://www.city.kitakyushu.lg.jp/sigikai/file_0056.html'),

-- 北区 (市町村)
('北区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '北区' AND type = '市町村'), 'https://www.city.kita.lg.jp/assembly/members/1020017.html'),

-- 千代田区 (市町村)
('千代田区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '千代田区' AND type = '市町村'), 'https://gikai-chiyoda-tokyo.jp/about/giin/index.html'),

-- 千葉市 (市町村)
('千葉市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '千葉市' AND type = '市町村'), 'https://www.city.chiba.jp/shigikai/gojuon.html'),

-- 台東区 (市町村)
('台東区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '台東区' AND type = '市町村'), 'https://taito.gijiroku.com/voices/g07_giinlistP.asp'),

-- 名古屋市 (市町村)
('名古屋市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '名古屋市' AND type = '市町村'), 'https://www.city.nagoya.jp/shikai/category/333-4-0-0-0-0-0-0-0-0.html'),

-- 品川区 (市町村)
('品川区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '品川区' AND type = '市町村'), 'https://gikai.city.shinagawa.tokyo.jp/profile/50on'),

-- 堺市 (市町村)
('堺市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '堺市' AND type = '市町村'), 'https://www.city.sakai.lg.jp/shigikai/meibo/50on.html'),

-- 墨田区 (市町村)
('墨田区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '墨田区' AND type = '市町村'), 'https://www.city.sumida.lg.jp/kugikai/kousei/giinmeibo06.html'),

-- 大田区 (市町村)
('大田区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '大田区' AND type = '市町村'), 'https://www.city.ota.tokyo.jp/gikai/shoukai/giinsyokai.html'),

-- 大阪市 (市町村)
('大阪市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '大阪市' AND type = '市町村'), 'https://www.city.osaka.lg.jp/shikai/category/3559-2-0-0-0-0-0-0-0-0.html'),

-- 岡山市 (市町村)
('岡山市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '岡山市' AND type = '市町村'), 'https://www.city.okayama.jp/gikai/0000015787.html'),

-- 川崎市 (市町村)
('川崎市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '川崎市' AND type = '市町村'), 'https://www.city.kawasaki.jp/shisei/category/40-3-1-0-0-0-0-0-0-0.html'),

-- 広島市 (市町村)
('広島市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '広島市' AND type = '市町村'), 'https://www.city.hiroshima.lg.jp/gikai/giin-shoukai/1014892/index.html'),

-- 文京区 (市町村)
('文京区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '文京区' AND type = '市町村'), 'https://www.city.bunkyo.lg.jp/kugikai/p007041.html'),

-- 新宿区 (市町村)
('新宿区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '新宿区' AND type = '市町村'), 'https://www.city.shinjuku.lg.jp/kusei/gikai01_000112.html'),

-- 新潟市 (市町村)
('新潟市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '新潟市' AND type = '市町村'), 'https://www.city.niigata.lg.jp/shigikai/index_meibo/meibo_01kubetsu.html'),

-- 札幌市 (市町村)
('札幌市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '札幌市' AND type = '市町村'), 'https://www.city.sapporo.jp/gikai/html/giin.html'),

-- 杉並区 (市町村)
('杉並区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '杉並区' AND type = '市町村'), 'https://suginami.gijiroku.com/voices/g07_giinlist_s.asp'),

-- 板橋区 (市町村)
('板橋区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '板橋区' AND type = '市町村'), 'https://www.city.itabashi.tokyo.jp/kugikai/giin/1010916.html'),

-- 横浜市 (市町村)
('横浜市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '横浜市' AND type = '市町村'), 'https://www.city.yokohama.lg.jp/shikai/giin/50on.html'),

-- 江戸川区 (市町村)
('江戸川区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '江戸川区' AND type = '市町村'), 'https://www.gikai.city.edogawa.tokyo.jp/g07_giinlistP.asp'),

-- 江東区 (市町村)
('江東区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '江東区' AND type = '市町村'), 'https://www.city.koto.lg.jp/kuse/kugikai/shokai/gisekijun/index.html'),

-- 浜松市 (市町村)
('浜松市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '浜松市' AND type = '市町村'), 'https://www.city.hamamatsu.shizuoka.jp/gikai/iinkai/meibo50.html'),

-- 渋谷区 (市町村)
('渋谷区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '渋谷区' AND type = '市町村'), 'https://shibukugi.tokyo/giin/2023012400017/'),

-- 港区 (市町村)
('港区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '港区' AND type = '市町村'), 'https://gikai2.city.minato.tokyo.jp/g07_giinlist_s.asp'),

-- 熊本市 (市町村)
('熊本市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '熊本市' AND type = '市町村'), 'https://kumamoto-shigikai.jp/namelist/pub/list50.aspx?c_id=3'),

-- 目黒区 (市町村)
('目黒区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '目黒区' AND type = '市町村'), 'https://www.city.meguro.tokyo.jp/kugikai/kusei/kugikai/giseki_jun.html'),

-- 相模原市 (市町村)
('相模原市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '相模原市' AND type = '市町村'), 'https://www.sagamihara-shigikai.jp/category/category/meibo/'),

-- 神戸市 (市町村)
('神戸市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '神戸市' AND type = '市町村'), 'https://www.city.kobe.lg.jp/a71064/shise/municipal/giinnmeibo/50onmeibo.html'),

-- 福岡市 (市町村)
('福岡市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '福岡市' AND type = '市町村'), 'https://gikai.city.fukuoka.lg.jp/member/alphabet/'),

-- 練馬区 (市町村)
('練馬区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '練馬区' AND type = '市町村'), 'https://www.city.nerima.tokyo.jp/gikai/giin/50on/index.html'),

-- 荒川区 (市町村)
('荒川区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '荒川区' AND type = '市町村'), 'https://www.city.arakawa.tokyo.jp/a053/gikaisenkyo/kugikai/giinmeibo.html'),

-- 葛飾区 (市町村)
('葛飾区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '葛飾区' AND type = '市町村'), 'https://smart.discussvision.net/smart/tenant/katsushika/WebView/rd/speaker.html'),

-- 豊島区 (市町村)
('豊島区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '豊島区' AND type = '市町村'), 'https://www.city.toshima.lg.jp/366/kuse/gikai/ginichiran/mebo/2404241622.html'),

-- 足立区 (市町村)
('足立区議会', '区議会', (SELECT id FROM governing_bodies WHERE name = '足立区' AND type = '市町村'), 'https://www.gikai-adachi.jp/g07_giinlist_s.asp'),

-- 静岡市 (市町村)
('静岡市議会', '市議会', (SELECT id FROM governing_bodies WHERE name = '静岡市' AND type = '市町村'), 'https://www.city.shizuoka.lg.jp/gikai/s900078.html')
ON CONFLICT (name, governing_body_id) DO NOTHING;
