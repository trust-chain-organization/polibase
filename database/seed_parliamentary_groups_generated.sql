-- Generated from database on 2025-07-13 04:09:27
-- parliamentary_groups seed data

INSERT INTO parliamentary_groups (name, conference_id, url, description, is_active) VALUES
ON CONFLICT (name, conference_id) DO NOTHING;
