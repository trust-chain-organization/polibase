-- Add user_id foreign keys to work-related tables for traceability

-- Add reviewed_by_user_id to extracted_politicians table
ALTER TABLE extracted_politicians
ADD COLUMN reviewed_by_user_id UUID REFERENCES users(user_id);

CREATE INDEX idx_extracted_politicians_reviewed_by_user_id
ON extracted_politicians(reviewed_by_user_id);

COMMENT ON COLUMN extracted_politicians.reviewed_by_user_id IS 'レビューを実行したユーザーID（UUID）';

-- Add reviewed_by_user_id to extracted_parliamentary_group_members table
ALTER TABLE extracted_parliamentary_group_members
ADD COLUMN reviewed_by_user_id UUID REFERENCES users(user_id);

CREATE INDEX idx_extracted_parliamentary_group_members_reviewed_by_user_id
ON extracted_parliamentary_group_members(reviewed_by_user_id);

COMMENT ON COLUMN extracted_parliamentary_group_members.reviewed_by_user_id IS 'レビューを実行したユーザーID（UUID）';

-- Add matched_by_user_id to speakers table (for future use)
ALTER TABLE speakers
ADD COLUMN matched_by_user_id UUID REFERENCES users(user_id);

CREATE INDEX idx_speakers_matched_by_user_id
ON speakers(matched_by_user_id);

COMMENT ON COLUMN speakers.matched_by_user_id IS '発言者と政治家の紐付けを実行したユーザーID（UUID）';
