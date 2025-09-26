-- Migrate existing politicians data to extracted_politicians table
-- This migration copies all existing politicians to extracted_politicians with 'approved' status
-- Since these are already in the system, they're considered approved

-- Insert existing politicians data into extracted_politicians
INSERT INTO extracted_politicians (
    name,
    party_id,
    district,
    position,
    profile_url,
    image_url,
    status,
    extracted_at,
    reviewed_at,
    reviewer_id,
    created_at,
    updated_at
)
SELECT
    p.name,
    p.political_party_id AS party_id,
    p.electoral_district AS district,
    p.position,
    p.profile_url,
    NULL AS image_url,  -- No image_url in current politicians table
    'approved' AS status,  -- Mark as approved since they're already in production
    COALESCE(p.created_at, CURRENT_TIMESTAMP) AS extracted_at,
    COALESCE(p.created_at, CURRENT_TIMESTAMP) AS reviewed_at,  -- Use creation time as review time
    NULL AS reviewer_id,  -- No reviewer information available for historical data
    p.created_at,
    p.updated_at
FROM politicians p
WHERE NOT EXISTS (
    -- Prevent duplicate entries if migration is run multiple times
    SELECT 1
    FROM extracted_politicians ep
    WHERE ep.name = p.name
        AND (ep.party_id = p.political_party_id OR (ep.party_id IS NULL AND p.political_party_id IS NULL))
);

-- Add a comment to document this migration
COMMENT ON TABLE extracted_politicians IS 'LLMが抽出した政治家データの中間テーブル（レビュー前）。既存のpoliticiansテーブルのデータは承認済みとして移行済み。';

-- Log migration completion
DO $$
DECLARE
    migrated_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO migrated_count
    FROM extracted_politicians
    WHERE status = 'approved';

    RAISE NOTICE 'Migration completed. % politicians migrated to extracted_politicians table with approved status.', migrated_count;
END $$;
