-- Add members_list_url column to political_parties table
ALTER TABLE political_parties
ADD COLUMN IF NOT EXISTS members_list_url TEXT;

-- Add comment to describe the column
COMMENT ON COLUMN political_parties.members_list_url IS '議員一覧ページのURL';
