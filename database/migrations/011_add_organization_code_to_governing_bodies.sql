-- Add organization_code column to governing_bodies table
-- This column stores the 6-digit local government code from the Ministry of Internal Affairs and Communications

-- Add organization_code column
ALTER TABLE governing_bodies
ADD COLUMN organization_code CHAR(6) UNIQUE;

-- Add more detailed type classification
ALTER TABLE governing_bodies
ADD COLUMN organization_type VARCHAR(20);

-- Update type classification based on existing type values
UPDATE governing_bodies
SET organization_type = CASE
    WHEN type = '国' THEN '国'
    WHEN type = '都道府県' THEN '都道府県'
    WHEN type = '市町村' THEN '市町村'
    ELSE type
END;

-- Add comments to explain the columns
COMMENT ON COLUMN governing_bodies.organization_code IS '総務省の6桁地方自治体コード';
COMMENT ON COLUMN governing_bodies.organization_type IS '詳細な組織種別（都道府県、市、区、町、村など）';
