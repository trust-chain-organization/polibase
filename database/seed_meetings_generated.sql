-- Generated from database on 2025-07-27 09:34:39
-- meetings seed data

INSERT INTO meetings (conference_id, date, url, gcs_pdf_uri, gcs_text_uri) VALUES
((SELECT c.id FROM conferences c JOIN governing_bodies gb ON c.governing_body_id = gb.id WHERE c.name = '産業交通水道委員会' AND gb.name = '京都府京都市' AND gb.type = '市町村'), '2025-03-25', 'https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=6077&schedule_id=1&is_search=false&view_years=2025', NULL, 'gs://polibase-scraped-minutes/scraped/2025/03/25/6077_1.txt')
;
