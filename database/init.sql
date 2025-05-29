-- Database Schema for Political Activity Tracking Application
-- Generated from polibase.dbml

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 開催主体テーブル
CREATE TABLE governing_bodies (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    type VARCHAR, -- 例: "国", "都道府県", "市町村"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 会議体テーブル (議会や委員会など)
CREATE TABLE conferences (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    type VARCHAR, -- 例: "国会全体", "議院", "地方議会全体", "常任委員会"
    governing_body_id INTEGER NOT NULL REFERENCES governing_bodies(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 会議テーブル (具体的な開催インスタンス)
CREATE TABLE meetings (
    id SERIAL PRIMARY KEY,
    conference_id INTEGER NOT NULL REFERENCES conferences(id),
    date DATE, -- 開催日
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 議事録テーブル
CREATE TABLE minutes (
    id SERIAL PRIMARY KEY,
    url VARCHAR, -- 議事録PDFなどのURL
    meeting_id INTEGER NOT NULL REFERENCES meetings(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 発言者テーブル
CREATE TABLE speakers (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL, -- 発言者名
    type VARCHAR, -- 例: "政治家", "参考人", "議長", "政府職員"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 政党テーブル
CREATE TABLE political_parties (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE, -- 政党名 (重複なし)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 政治家テーブル
CREATE TABLE politicians (
    id SERIAL PRIMARY KEY, -- 政治家固有のID
    name VARCHAR NOT NULL, -- 政治家名
    political_party_id INTEGER REFERENCES political_parties(id), -- 現在の主要所属政党
    speaker_id INTEGER UNIQUE NOT NULL REFERENCES speakers(id), -- 各政治家は一意の発言者でもある (1対1関係)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 公約テーブル
CREATE TABLE pledges (
    id SERIAL PRIMARY KEY,
    politician_id INTEGER NOT NULL REFERENCES politicians(id), -- どの政治家の公約か
    title VARCHAR NOT NULL, -- 公約のタイトル
    content TEXT, -- 公約の詳細内容
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 政治家の政党所属履歴テーブル
CREATE TABLE party_membership_history (
    id SERIAL PRIMARY KEY,
    politician_id INTEGER NOT NULL REFERENCES politicians(id), -- どの政治家の所属履歴か
    political_party_id INTEGER NOT NULL REFERENCES political_parties(id), -- どの政党に所属していたか
    start_date DATE NOT NULL, -- 所属開始日
    end_date DATE, -- 所属終了日 (現所属の場合はNULL)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 発言テーブル
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    minutes_id INTEGER NOT NULL REFERENCES minutes(id), -- どの議事録の発言か
    speaker_id INTEGER NOT NULL REFERENCES speakers(id), -- どの発言者の発言か
    comment TEXT NOT NULL, -- 発言内容
    sequence_number INTEGER NOT NULL, -- 議事録内の発言順序
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 同一議事録内での発言順序は一意
    UNIQUE(minutes_id, sequence_number)
);

-- 議案テーブル
CREATE TABLE proposals (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL, -- 議案内容
    status VARCHAR, -- 例: "審議中", "可決", "否決"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 議案への賛否情報テーブル (誰が議案に賛成したか)
CREATE TABLE proposal_judges (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id), -- どの議案に対する賛否か
    politician_id INTEGER NOT NULL REFERENCES politicians(id), -- どの政治家の賛否か
    politician_party_id INTEGER REFERENCES political_parties(id), -- 票決時の所属政党
    approve VARCHAR, -- 例: "賛成", "反対", "棄権", "欠席"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 議員の議会所属情報テーブル
CREATE TABLE politician_affiliations (
    id SERIAL PRIMARY KEY,
    politician_id INTEGER NOT NULL REFERENCES politicians(id), -- どの政治家の所属情報か
    conference_id INTEGER NOT NULL REFERENCES conferences(id), -- どの会議体（議会・委員会）に所属しているか
    start_date DATE NOT NULL, -- 所属開始日
    end_date DATE, -- 所属終了日 (現所属の場合はNULL)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 議案と会議の紐付け情報テーブル（議案の会議経過）
CREATE TABLE proposal_meeting_occurrences (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id), -- どの議案か
    meeting_id INTEGER NOT NULL REFERENCES meetings(id), -- どの会議で扱われたか
    occurrence_type VARCHAR, -- 例: "提出", "審議", "委員会採決", "本会議採決"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックスの作成
CREATE INDEX idx_conferences_governing_body ON conferences(governing_body_id);
CREATE INDEX idx_meetings_conference ON meetings(conference_id);
CREATE INDEX idx_minutes_meeting ON minutes(meeting_id);
CREATE INDEX idx_politicians_political_party ON politicians(political_party_id);
CREATE INDEX idx_politicians_speaker ON politicians(speaker_id);
CREATE INDEX idx_pledges_politician ON pledges(politician_id);
CREATE INDEX idx_party_membership_politician ON party_membership_history(politician_id);
CREATE INDEX idx_party_membership_party ON party_membership_history(political_party_id);
CREATE INDEX idx_conversations_minutes ON conversations(minutes_id);
CREATE INDEX idx_conversations_speaker ON conversations(speaker_id);
CREATE INDEX idx_proposal_judges_proposal ON proposal_judges(proposal_id);
CREATE INDEX idx_proposal_judges_politician ON proposal_judges(politician_id);
CREATE INDEX idx_politician_affiliations_politician ON politician_affiliations(politician_id);
CREATE INDEX idx_politician_affiliations_conference ON politician_affiliations(conference_id);
CREATE INDEX idx_proposal_meeting_occurrences_proposal ON proposal_meeting_occurrences(proposal_id);
CREATE INDEX idx_proposal_meeting_occurrences_meeting ON proposal_meeting_occurrences(meeting_id);

-- トリガー関数：updated_atカラムを自動更新
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 各テーブルにupdated_atトリガーを設定
CREATE TRIGGER update_governing_bodies_updated_at BEFORE UPDATE ON governing_bodies FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_conferences_updated_at BEFORE UPDATE ON conferences FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_meetings_updated_at BEFORE UPDATE ON meetings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_minutes_updated_at BEFORE UPDATE ON minutes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_speakers_updated_at BEFORE UPDATE ON speakers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_political_parties_updated_at BEFORE UPDATE ON political_parties FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_politicians_updated_at BEFORE UPDATE ON politicians FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_pledges_updated_at BEFORE UPDATE ON pledges FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_party_membership_history_updated_at BEFORE UPDATE ON party_membership_history FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_proposals_updated_at BEFORE UPDATE ON proposals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_proposal_judges_updated_at BEFORE UPDATE ON proposal_judges FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_politician_affiliations_updated_at BEFORE UPDATE ON politician_affiliations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_proposal_meeting_occurrences_updated_at BEFORE UPDATE ON proposal_meeting_occurrences FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- サンプルデータの挿入（テスト用）
INSERT INTO governing_bodies (name, type) VALUES 
('日本国', '国'),
('東京都', '都道府県'),
('千代田区', '市町村');

INSERT INTO political_parties (name) VALUES 
('自民党'),
('立憲民主党'),
('公明党'),
('日本維新の会'),
('国民民主党');

COMMENT ON TABLE governing_bodies IS '開催主体';
COMMENT ON TABLE conferences IS '会議体 (議会や委員会など)';
COMMENT ON TABLE meetings IS '会議 (具体的な開催インスタンス)';
COMMENT ON TABLE minutes IS '議事録';
COMMENT ON TABLE speakers IS '発言者';
COMMENT ON TABLE political_parties IS '政党';
COMMENT ON TABLE politicians IS '政治家';
COMMENT ON TABLE pledges IS '公約';
COMMENT ON TABLE party_membership_history IS '政治家の政党所属履歴';
COMMENT ON TABLE conversations IS '発言';
COMMENT ON TABLE proposals IS '議案';
COMMENT ON TABLE proposal_judges IS '議案への賛否情報 (誰が議案に賛成したか)';
COMMENT ON TABLE politician_affiliations IS '議員の議会所属情報';
COMMENT ON TABLE proposal_meeting_occurrences IS '議案と会議の紐付け情報（議案の会議経過）';
