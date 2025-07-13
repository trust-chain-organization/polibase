-- Generated from database on 2025-07-13 02:28:44
-- political_parties seed data

INSERT INTO political_parties (name, members_list_url) VALUES
('NHK党', 'https://www.syoha.jp/%E5%85%9A%E5%BD%B9%E5%93%A1-%E8%AD%B0%E5%93%A1/'),
('れいわ新選組', 'https://reiwa-shinsengumi.com/member/'),
('公明党', 'https://www.komei.or.jp/member/'),
('参政党', 'https://sanseito.jp/2020/member/'),
('国民民主党', 'https://new-kokumin.jp/member'),
('大阪維新の会', 'https://oneosaka.jp/member/'),
('日本共産党', 'https://www.jcp.or.jp/giin/'),
('日本維新の会', 'https://o-ishin.jp/member/'),
('減税日本', 'http://genzeinippon.com/koho/'),
('新党やまと', 'https://yamato-party.jp/election/'),
('政権交代によるコロナ対策強化新党', NULL),
('日本第一党', 'https://japan-first.net/members/'),
('新党くにもり', NULL),
('愛地球党', NULL),
('無所属', NULL),
('社民党', 'https://sdp.or.jp/local-assembly/'),
('立憲民主党', 'https://cdp-japan.jp/members/all'),
('自由民主党', 'https://www.jimin.jp/member/search/'),
('都民ファーストの会', 'https://tomin1st.jp/#Members')
ON CONFLICT (name) DO NOTHING;
