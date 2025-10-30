# Migration Examples

This document provides real-world migration examples from the Polibase project.

## Example 1: Creating a New Table

Based on `013_create_llm_processing_history.sql`:

```sql
-- Migration: 013 - Create LLM processing history table
-- Description: Track LLM API calls for auditing and debugging
-- Date: 2025-01-15

CREATE TABLE IF NOT EXISTS llm_processing_history (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Request information
    prompt TEXT NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    temperature NUMERIC(3,2),

    -- Response information
    response TEXT,
    tokens_used INTEGER,
    processing_time_ms INTEGER,

    -- Metadata
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    request_metadata JSONB,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_llm_history_created
    ON llm_processing_history(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_llm_history_status
    ON llm_processing_history(status)
    WHERE status != 'completed';  -- Partial index

CREATE INDEX IF NOT EXISTS idx_llm_history_model
    ON llm_processing_history(model_name, created_at DESC);

-- Comments
COMMENT ON TABLE llm_processing_history IS 'History of LLM API calls for auditing and debugging';
COMMENT ON COLUMN llm_processing_history.prompt IS 'Input prompt sent to LLM';
COMMENT ON COLUMN llm_processing_history.tokens_used IS 'Number of tokens consumed';
COMMENT ON COLUMN llm_processing_history.request_metadata IS 'Additional request context in JSON format';
```

## Example 2: Adding Columns

Based on `004_add_gcs_uri_to_meetings.sql`:

```sql
-- Migration: 004 - Add GCS URI columns to meetings
-- Description: Support Google Cloud Storage integration for meeting documents
-- Date: 2024-12-01

-- Add GCS URI columns
ALTER TABLE meetings
    ADD COLUMN IF NOT EXISTS gcs_pdf_uri VARCHAR(500),
    ADD COLUMN IF NOT EXISTS gcs_text_uri VARCHAR(500);

-- Add comments
COMMENT ON COLUMN meetings.gcs_pdf_uri IS 'Google Cloud Storage URI for PDF file (gs://bucket/path)';
COMMENT ON COLUMN meetings.gcs_text_uri IS 'Google Cloud Storage URI for extracted text file';

-- Create index for queries filtering by GCS files
CREATE INDEX IF NOT EXISTS idx_meetings_has_gcs_files
    ON meetings(id)
    WHERE gcs_pdf_uri IS NOT NULL;
```

## Example 3: Adding a Column with Data Migration

Based on `006_add_role_to_politician_affiliations.sql`:

```sql
-- Migration: 006 - Add role column to politician_affiliations
-- Description: Track politician roles in conferences (e.g., 議長, 副議長)
-- Date: 2024-12-10

-- Step 1: Add nullable column
ALTER TABLE politician_affiliations
    ADD COLUMN IF NOT EXISTS role VARCHAR(100);

-- Step 2: Populate default value for existing rows
UPDATE politician_affiliations
    SET role = '議員'
    WHERE role IS NULL;

-- Step 3: Add constraint (optional - keep nullable for now)
-- ALTER TABLE politician_affiliations
--     ALTER COLUMN role SET NOT NULL;

-- Add comment
COMMENT ON COLUMN politician_affiliations.role IS
    'Role in conference (e.g., 議長, 副議長, 委員長, 議員)';

-- Create index for role queries
CREATE INDEX IF NOT EXISTS idx_politician_affiliations_role
    ON politician_affiliations(role);
```

## Example 4: Creating Staging Table

Based on `007_create_extracted_conference_members_table.sql`:

```sql
-- Migration: 007 - Create extracted conference members staging table
-- Description: Staging table for conference member extraction and matching
-- Date: 2024-12-15

CREATE TABLE IF NOT EXISTS extracted_conference_members (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Conference reference
    conference_id INTEGER NOT NULL,

    -- Extracted data
    name VARCHAR(255) NOT NULL,
    party VARCHAR(255),
    role VARCHAR(100),
    raw_text TEXT,

    -- Matching results
    matched_politician_id INTEGER,
    match_confidence NUMERIC(3,2),
    matching_status VARCHAR(50) NOT NULL DEFAULT 'pending',

    -- Metadata
    extraction_metadata JSONB,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    matched_at TIMESTAMP,

    -- Foreign keys
    CONSTRAINT fk_extracted_members_conference
        FOREIGN KEY (conference_id)
        REFERENCES conferences(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_extracted_members_politician
        FOREIGN KEY (matched_politician_id)
        REFERENCES politicians(id)
        ON DELETE SET NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_extracted_members_conference
    ON extracted_conference_members(conference_id);

CREATE INDEX IF NOT EXISTS idx_extracted_members_status
    ON extracted_conference_members(matching_status);

CREATE INDEX IF NOT EXISTS idx_extracted_members_politician
    ON extracted_conference_members(matched_politician_id);

-- Comments
COMMENT ON TABLE extracted_conference_members IS
    'Staging table for conference member extraction and matching workflow';
COMMENT ON COLUMN extracted_conference_members.matching_status IS
    'Status: pending, matched, needs_review, no_match';
COMMENT ON COLUMN extracted_conference_members.match_confidence IS
    'Confidence score for politician match (0.0-1.0)';
```

## Example 5: Creating Related Tables

Based on `008_create_parliamentary_groups_tables.sql`:

```sql
-- Migration: 008 - Create parliamentary groups tables
-- Description: Support parliamentary groups (議員団/会派) management
-- Date: 2024-12-20

-- Main parliamentary groups table
CREATE TABLE IF NOT EXISTS parliamentary_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    conference_id INTEGER NOT NULL,
    description TEXT,
    website_url VARCHAR(500),
    members_list_url VARCHAR(500),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key
    CONSTRAINT fk_parliamentary_groups_conference
        FOREIGN KEY (conference_id)
        REFERENCES conferences(id)
        ON DELETE CASCADE,

    -- Unique constraint
    CONSTRAINT uq_parliamentary_groups_name_conference
        UNIQUE (name, conference_id)
);

-- Parliamentary group memberships table
CREATE TABLE IF NOT EXISTS parliamentary_group_memberships (
    id SERIAL PRIMARY KEY,
    parliamentary_group_id INTEGER NOT NULL,
    politician_id INTEGER NOT NULL,
    role VARCHAR(100),
    start_date DATE NOT NULL,
    end_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Foreign keys
    CONSTRAINT fk_pg_memberships_group
        FOREIGN KEY (parliamentary_group_id)
        REFERENCES parliamentary_groups(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_pg_memberships_politician
        FOREIGN KEY (politician_id)
        REFERENCES politicians(id)
        ON DELETE CASCADE,

    -- Ensure no overlapping memberships
    CONSTRAINT chk_pg_memberships_dates
        CHECK (end_date IS NULL OR end_date > start_date)
);

-- Indexes for parliamentary_groups
CREATE INDEX IF NOT EXISTS idx_parliamentary_groups_conference
    ON parliamentary_groups(conference_id);

CREATE INDEX IF NOT EXISTS idx_parliamentary_groups_name
    ON parliamentary_groups(name);

-- Indexes for memberships
CREATE INDEX IF NOT EXISTS idx_pg_memberships_group
    ON parliamentary_group_memberships(parliamentary_group_id);

CREATE INDEX IF NOT EXISTS idx_pg_memberships_politician
    ON parliamentary_group_memberships(politician_id);

CREATE INDEX IF NOT EXISTS idx_pg_memberships_dates
    ON parliamentary_group_memberships(start_date, end_date);

-- Comments
COMMENT ON TABLE parliamentary_groups IS
    'Parliamentary groups (議員団/会派) within conferences';
COMMENT ON TABLE parliamentary_group_memberships IS
    'Tracks politician membership in parliamentary groups over time';
COMMENT ON COLUMN parliamentary_group_memberships.role IS
    'Role in group (e.g., 団長, 幹事長, 幹事, 一般)';
```

## Example 6: Adding Organization Code

Based on `011_add_organization_code_to_governing_bodies.sql`:

```sql
-- Migration: 011 - Add organization code to governing bodies
-- Description: Track organization codes for coverage analysis
-- Date: 2025-01-10

-- Add columns
ALTER TABLE governing_bodies
    ADD COLUMN IF NOT EXISTS organization_code VARCHAR(20),
    ADD COLUMN IF NOT EXISTS organization_type VARCHAR(50);

-- Add unique constraint on organization code
ALTER TABLE governing_bodies
    ADD CONSTRAINT uq_governing_bodies_org_code
        UNIQUE (organization_code);

-- Create index
CREATE INDEX IF NOT EXISTS idx_governing_bodies_org_code
    ON governing_bodies(organization_code);

CREATE INDEX IF NOT EXISTS idx_governing_bodies_org_type
    ON governing_bodies(organization_type);

-- Add comments
COMMENT ON COLUMN governing_bodies.organization_code IS
    'Organization code from government registry (e.g., 131008 for Tokyo)';
COMMENT ON COLUMN governing_bodies.organization_type IS
    'Type: 国, 都道府県, 市区町村';
```

## Example 7: Creating Enum Type

```sql
-- Migration: XXX - Create status enum
-- Description: Add enum type for entity status

-- Create enum (idempotent)
DO $$ BEGIN
    CREATE TYPE entity_status AS ENUM (
        'pending',
        'active',
        'inactive',
        'archived'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Use in existing table
ALTER TABLE table_name
    ADD COLUMN IF NOT EXISTS status entity_status DEFAULT 'pending';

-- Or create new table with enum
CREATE TABLE IF NOT EXISTS new_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    status entity_status NOT NULL DEFAULT 'active'
);
```

## Example 8: Complex Data Migration

```sql
-- Migration: XXX - Migrate legacy data format
-- Description: Convert old format to new structure

DO $$
DECLARE
    rec RECORD;
    new_value TEXT;
BEGIN
    -- Process each record
    FOR rec IN SELECT * FROM table_name WHERE old_field IS NOT NULL AND new_field IS NULL
    LOOP
        -- Complex transformation
        new_value := CONCAT(
            UPPER(SUBSTRING(rec.old_field, 1, 1)),
            LOWER(SUBSTRING(rec.old_field, 2))
        );

        -- Update record
        UPDATE table_name
            SET new_field = new_value,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = rec.id;

        -- Log progress every 100 records
        IF rec.id % 100 = 0 THEN
            RAISE NOTICE 'Processed % records', rec.id;
        END IF;
    END LOOP;

    RAISE NOTICE 'Data migration completed';
END $$;
```

## Example 9: Adding Composite Index

```sql
-- Migration: XXX - Add composite index for performance
-- Description: Optimize queries filtering by multiple columns

-- For queries like: WHERE conference_id = ? AND status = ? ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_affiliations_conference_status_date
    ON politician_affiliations(conference_id, status, created_at DESC);

-- For queries like: WHERE politician_id = ? AND start_date <= ? AND (end_date IS NULL OR end_date >= ?)
CREATE INDEX IF NOT EXISTS idx_memberships_politician_dates
    ON parliamentary_group_memberships(politician_id, start_date, end_date);
```

## Example 10: Conditional Migration

```sql
-- Migration: XXX - Conditional schema update
-- Description: Only apply changes if certain conditions met

DO $$
BEGIN
    -- Check if column exists
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'table_name' AND column_name = 'new_column'
    ) THEN
        ALTER TABLE table_name ADD COLUMN new_column VARCHAR(255);
        RAISE NOTICE 'Added new_column';
    ELSE
        RAISE NOTICE 'Column already exists, skipping';
    END IF;

    -- Check table row count before expensive operation
    IF (SELECT COUNT(*) FROM table_name) < 10000 THEN
        -- Safe to do synchronous update
        UPDATE table_name SET new_column = old_column;
    ELSE
        RAISE NOTICE 'Table too large, update manually or in batches';
    END IF;
END $$;
```

## Anti-Patterns to Avoid

### ❌ Bad: Non-Idempotent

```sql
-- Will fail on second run
CREATE TABLE my_table (...);
ALTER TABLE my_table ADD COLUMN my_column VARCHAR(255);
```

### ✅ Good: Idempotent

```sql
-- Safe to run multiple times
CREATE TABLE IF NOT EXISTS my_table (...);
ALTER TABLE my_table ADD COLUMN IF NOT EXISTS my_column VARCHAR(255);
```

### ❌ Bad: Missing Foreign Key Index

```sql
-- Slow joins without index
ALTER TABLE speakers
    ADD CONSTRAINT fk_speakers_politicians
    FOREIGN KEY (politician_id) REFERENCES politicians(id);
```

### ✅ Good: Index on Foreign Key

```sql
-- Fast joins with index
ALTER TABLE speakers
    ADD CONSTRAINT fk_speakers_politicians
    FOREIGN KEY (politician_id) REFERENCES politicians(id);

CREATE INDEX IF NOT EXISTS idx_speakers_politician
    ON speakers(politician_id);
```

### ❌ Bad: Immediate NOT NULL

```sql
-- Fails if table has data
ALTER TABLE politicians
    ADD COLUMN email VARCHAR(255) NOT NULL;
```

### ✅ Good: Three-Step NOT NULL

```sql
-- Step 1: Add nullable
ALTER TABLE politicians ADD COLUMN IF NOT EXISTS email VARCHAR(255);

-- Step 2: Populate
UPDATE politicians SET email = CONCAT(LOWER(name), '@example.com') WHERE email IS NULL;

-- Step 3: Add constraint
ALTER TABLE politicians ALTER COLUMN email SET NOT NULL;
```
