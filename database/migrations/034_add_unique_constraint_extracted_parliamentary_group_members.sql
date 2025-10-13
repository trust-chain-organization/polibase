-- Add unique constraint to prevent duplicate extracted parliamentary group members
-- This ensures that we don't create multiple records for the same person in the same parliamentary group

-- First, remove any existing duplicates (keep the newest record for each group+name combination)
DELETE FROM extracted_parliamentary_group_members
WHERE id NOT IN (
    SELECT MAX(id)
    FROM extracted_parliamentary_group_members
    GROUP BY parliamentary_group_id, extracted_name
);

-- Add unique constraint
ALTER TABLE extracted_parliamentary_group_members
ADD CONSTRAINT unique_parliamentary_group_member
UNIQUE (parliamentary_group_id, extracted_name);

-- Add comment
COMMENT ON CONSTRAINT unique_parliamentary_group_member
ON extracted_parliamentary_group_members
IS '同じ議員団内で同じ名前の議員が重複して登録されることを防ぐ制約';
