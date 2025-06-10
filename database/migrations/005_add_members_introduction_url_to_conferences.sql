-- Add members_introduction_url column to conferences table
ALTER TABLE conferences
ADD COLUMN members_introduction_url VARCHAR(255);

-- Add comment to explain the column purpose
COMMENT ON COLUMN conferences.members_introduction_url IS 'URL where the council members of this conference are introduced';
