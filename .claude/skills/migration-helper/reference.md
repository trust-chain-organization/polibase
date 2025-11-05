# Migration Helper Reference

This document provides detailed reference information for database migrations in Polibase.

## Migration System Architecture

### Migration Files

Polibase uses sequential numbered SQL migration files:

```
database/migrations/
├── 001_initial_schema.sql
├── 002_add_features.sql
├── 003_add_indexes.sql
...
└── 013_create_llm_processing_history.sql
```

### Migration Runner

`database/02_run_migrations.sql` is the **master list** that executes all migrations in order:

```sql
\echo 'Running migrations...'

\i /docker-entrypoint-initdb.d/migrations/001_initial_schema.sql
\i /docker-entrypoint-initdb.d/migrations/002_add_features.sql
...
\i /docker-entrypoint-initdb.d/migrations/013_create_llm_processing_history.sql

\echo 'Migrations completed successfully'
```

**CRITICAL**: Every new migration MUST be added to this file!

### Reset Script

`./reset-database.sh` drops and recreates the database, running all migrations from scratch. This is how you test migrations locally.

## Database Design Overview

Polibaseのデータベース設計の全体像を理解することで、適切なマイグレーションを作成できます。

### Master Data（マスターデータ）

シードファイルで事前に投入される固定データ：

#### governing_bodies（統治組織）
- 国、都道府県、市町村などの政府組織
- 日本全国の1,966自治体を組織コードで追跡
- マイグレーション: `001_initial_schema.sql`
- シードデータ: `database/seeds/`

#### conferences（会議）
- 立法機関と委員会
- 国会、地方議会、常任委員会など
- `members_introduction_url` カラムでメンバー紹介ページを管理
- マイグレーション: `005_add_members_introduction_url_to_conferences.sql`

#### political_parties（政党）
- 政党マスターデータ
- `members_list_url` カラムでメンバーリストページを管理（Web scraping用）
- マイグレーション: `001_initial_schema.sql`

### Core Tables（コアテーブル）

アプリケーションの主要データを格納：

#### meetings（会議）
- 個別の会議セッション
- `gcs_pdf_uri`, `gcs_text_uri` カラムでGCS統合をサポート
- マイグレーション: `004_add_gcs_uri_to_meetings.sql`

#### minutes（議事録）
- 会議の議事録
- PDFまたはテキスト形式

#### speakers（話者）
- 議事録から抽出された話者
- `politicians` との多対多リンク可能

#### politicians（政治家）
- 政党Webサイトからスクレイピングされた政治家情報
- 政党所属とプロフィール情報を含む
- 名前 + 政党で重複チェック

#### conversations（会話）
- 議事録から抽出された個別の発言
- 話者と発言内容を紐付け
- `speakers` への外部キー

#### proposals（提案・議案）
- 立法提案と議案

#### politician_affiliations（政治家所属）
- 政治家と会議のメンバーシップ
- 役職（議長、副議長など）を含む
- マイグレーション: `006_add_role_to_politician_affiliations.sql`

#### extracted_conference_members（抽出された会議メンバー）
- 会議メンバー抽出の段階的処理用ステージングテーブル
- ステータス: pending, matched, needs_review, no_match
- マイグレーション: `007_create_extracted_conference_members_table.sql`

#### parliamentary_groups（議員団/会派）
- 会議内の議員グループ（議員団、会派）
- 投票ブロックを表現
- マイグレーション: `008_create_parliamentary_groups_tables.sql`

#### parliamentary_group_memberships（議員団メンバーシップ）
- 時系列で政治家の議員団所属を追跡
- 役職（団長、幹事長など）を含む
- マイグレーション: `008_create_parliamentary_groups_tables.sql`

### Repository Pattern

すべてのテーブルはClean Architectureのリポジトリパターンに従います：

```
src/domain/repositories/        # インターフェース定義
├── i_politician_repository.py
├── i_speaker_repository.py
└── ...

src/infrastructure/persistence/ # 実装
├── politician_repository_impl.py
├── speaker_repository_impl.py
└── ...
```

- `BaseRepository[T]`: 共通CRUD操作
- `ISessionAdapter`: データベースセッション抽象化
- すべてのリポジトリメソッドはasync/awaitを使用

### Key Migrations（主要なマイグレーション）

マイグレーションを作成する際の参考として：

- `004_add_gcs_uri_to_meetings.sql`: meetingsテーブルにGCS URIカラムを追加
- `005_add_members_introduction_url_to_conferences.sql`: conferencesにメンバーURLを追加
- `006_add_role_to_politician_affiliations.sql`: 所属に役職カラムを追加
- `007_create_extracted_conference_members_table.sql`: ステージングテーブル作成
- `008_create_parliamentary_groups_tables.sql`: 議員団と議員団メンバーシップテーブル作成
- `011_add_organization_code_to_governing_bodies.sql`: governing_bodiesに組織コードと組織タイプを追加

### Migration Workflow

新しいテーブルやカラムを追加する際：

1. **マイグレーションファイル作成**: `database/migrations/XXX_description.sql`
2. **02_run_migrations.sqlに追加**: 必須！
3. **Domain層更新**:
   - Entity: `src/domain/entities/`
   - Repository Interface: `src/domain/repositories/`
4. **Infrastructure層更新**:
   - Repository Implementation: `src/infrastructure/persistence/`
5. **テスト実行**: `./reset-database.sh`
6. **ドキュメント更新**: `docs/DATABASE_SCHEMA.md`

## Detailed Patterns

### Creating Tables

#### Basic Table

```sql
-- Migration: XXX - Create [table_name] table
-- Description: [Purpose of this table]
-- Date: [YYYY-MM-DD]

CREATE TABLE IF NOT EXISTS table_name (
    -- Primary key
    id SERIAL PRIMARY KEY,

    -- Required fields
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,

    -- Optional fields
    description TEXT,
    metadata JSONB,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Add comments
COMMENT ON TABLE table_name IS 'Description of what this table stores';
COMMENT ON COLUMN table_name.name IS 'Entity name';
COMMENT ON COLUMN table_name.status IS 'Current status (active, inactive, pending)';
```

#### Table with Foreign Keys

```sql
CREATE TABLE IF NOT EXISTS child_table (
    id SERIAL PRIMARY KEY,
    parent_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraint
    CONSTRAINT fk_child_parent
        FOREIGN KEY (parent_id)
        REFERENCES parent_table(id)
        ON DELETE CASCADE
);

-- Index on foreign key
CREATE INDEX IF NOT EXISTS idx_child_parent_id
    ON child_table(parent_id);
```

#### Table with Unique Constraints

```sql
CREATE TABLE IF NOT EXISTS unique_table (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(100) NOT NULL,

    -- Unique constraints
    CONSTRAINT uq_unique_table_email UNIQUE (email),
    CONSTRAINT uq_unique_table_username UNIQUE (username)
);

-- Or add after table creation
ALTER TABLE unique_table
    ADD CONSTRAINT uq_unique_table_email UNIQUE (email);
```

### Adding Columns

#### Simple Column Addition

```sql
-- Migration: XXX - Add [column] to [table]
-- Description: [Why this column is needed]

ALTER TABLE table_name
    ADD COLUMN IF NOT EXISTS column_name VARCHAR(255);

COMMENT ON COLUMN table_name.column_name IS 'Description';
```

#### Column with Default Value

```sql
ALTER TABLE table_name
    ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'pending';

-- Update existing rows (optional)
UPDATE table_name
    SET status = 'active'
    WHERE status IS NULL;
```

#### NOT NULL Column (Safe Pattern)

```sql
-- Step 1: Add nullable column
ALTER TABLE table_name
    ADD COLUMN IF NOT EXISTS email VARCHAR(255);

-- Step 2: Populate data
UPDATE table_name
    SET email = CONCAT(LOWER(name), '@example.com')
    WHERE email IS NULL;

-- Step 3: Add NOT NULL constraint
ALTER TABLE table_name
    ALTER COLUMN email SET NOT NULL;

-- Step 4: Add comment
COMMENT ON COLUMN table_name.email IS 'User email address';
```

### Creating Indexes

#### Single Column Index

```sql
-- Migration: XXX - Create index on [table].[column]
-- Description: Improve query performance for [specific query]

CREATE INDEX IF NOT EXISTS idx_table_column
    ON table_name(column_name);
```

#### Multi-Column Index

```sql
-- For queries like: WHERE column1 = ? AND column2 = ?
CREATE INDEX IF NOT EXISTS idx_table_column1_column2
    ON table_name(column1, column2);
```

#### Partial Index

```sql
-- Index only active records
CREATE INDEX IF NOT EXISTS idx_table_active
    ON table_name(created_at)
    WHERE status = 'active';
```

#### Unique Index

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_table_unique_column
    ON table_name(column_name);
```

### Adding Foreign Keys

#### Basic Foreign Key

```sql
-- Ensure referenced data exists first
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM parent_table WHERE id = 0) THEN
        INSERT INTO parent_table (id, name) VALUES (0, 'Unknown');
    END IF;
END $$;

-- Add foreign key
ALTER TABLE child_table
    ADD CONSTRAINT fk_child_parent
    FOREIGN KEY (parent_id)
    REFERENCES parent_table(id)
    ON DELETE SET NULL;  -- or CASCADE, RESTRICT
```

#### Foreign Key Options

```sql
-- CASCADE: Delete child rows when parent is deleted
ON DELETE CASCADE

-- SET NULL: Set child foreign key to NULL when parent is deleted
ON DELETE SET NULL

-- RESTRICT: Prevent parent deletion if children exist
ON DELETE RESTRICT

-- NO ACTION: Similar to RESTRICT (default)
ON DELETE NO ACTION
```

### Enum Types

#### Creating Enum

```sql
-- Create enum type (idempotent)
DO $$ BEGIN
    CREATE TYPE status_type AS ENUM ('pending', 'active', 'inactive');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Use in table
ALTER TABLE table_name
    ADD COLUMN IF NOT EXISTS status status_type DEFAULT 'pending';
```

#### Adding Enum Value

```sql
-- Add new value to existing enum
ALTER TYPE status_type ADD VALUE IF NOT EXISTS 'archived';
```

### Data Migrations

#### Simple Update

```sql
-- Update existing data
UPDATE table_name
    SET status = 'active'
    WHERE status IS NULL AND created_at < NOW() - INTERVAL '1 month';
```

#### Complex Data Migration

```sql
-- Migration with conditional logic
DO $$
DECLARE
    rec RECORD;
BEGIN
    FOR rec IN SELECT * FROM table_name WHERE needs_update = true
    LOOP
        -- Complex logic here
        UPDATE table_name
            SET new_field = calculated_value
            WHERE id = rec.id;
    END LOOP;
END $$;
```

### Renaming (Safe Patterns)

#### Renaming Column (Safe Way)

```sql
-- Step 1: Add new column
ALTER TABLE table_name
    ADD COLUMN IF NOT EXISTS new_name VARCHAR(255);

-- Step 2: Copy data
UPDATE table_name
    SET new_name = old_name
    WHERE new_name IS NULL;

-- Step 3: (Later migration) Drop old column after application updated
-- ALTER TABLE table_name DROP COLUMN IF EXISTS old_name;
```

#### Renaming Table

```sql
-- Only do this if absolutely necessary!
-- Requires application code update

ALTER TABLE old_table_name
    RENAME TO new_table_name;

-- Update dependent views, triggers, etc.
```

## Idempotency

**All migrations must be idempotent** (safe to run multiple times).

### Use IF NOT EXISTS / IF EXISTS

```sql
-- ✅ GOOD: Idempotent
CREATE TABLE IF NOT EXISTS my_table (...);
ALTER TABLE my_table ADD COLUMN IF NOT EXISTS my_column VARCHAR(255);
CREATE INDEX IF NOT EXISTS idx_my_index ON my_table(my_column);
DROP TABLE IF EXISTS old_table;

-- ❌ BAD: Not idempotent
CREATE TABLE my_table (...);  -- Fails on second run
ALTER TABLE my_table ADD COLUMN my_column VARCHAR(255);  -- Fails if exists
```

### DO Block for Complex Logic

```sql
DO $$ BEGIN
    -- Check condition before action
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'my_table') THEN
        CREATE TABLE my_table (...);
    END IF;
END $$;
```

## Performance Considerations

### Index Creation

Indexes speed up reads but slow down writes:

```sql
-- For large tables, create index concurrently (doesn't lock table)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_table_column
    ON table_name(column_name);
```

### Batch Updates

For large data migrations:

```sql
-- Update in batches to avoid long locks
DO $$
DECLARE
    batch_size INTEGER := 1000;
    rows_updated INTEGER;
BEGIN
    LOOP
        UPDATE table_name
        SET new_field = old_field
        WHERE new_field IS NULL
        AND id IN (
            SELECT id FROM table_name
            WHERE new_field IS NULL
            LIMIT batch_size
        );

        GET DIAGNOSTICS rows_updated = ROW_COUNT;
        EXIT WHEN rows_updated = 0;

        -- Commit each batch
        COMMIT;
    END LOOP;
END $$;
```

## Common Mistakes

### Mistake 1: Forgetting 02_run_migrations.sql

**Problem**: Migration file created but not added to run script

**Symptoms**:
- Works on your machine (manual apply)
- Fails on colleague's machine or CI
- Database inconsistency across environments

**Fix**: ALWAYS add to `02_run_migrations.sql`

### Mistake 2: Non-Idempotent Migrations

**Problem**:
```sql
ALTER TABLE politicians ADD COLUMN email VARCHAR(255);  -- Fails on re-run
```

**Fix**:
```sql
ALTER TABLE politicians ADD COLUMN IF NOT EXISTS email VARCHAR(255);
```

### Mistake 3: Adding NOT NULL Without Data

**Problem**:
```sql
ALTER TABLE politicians
    ADD COLUMN email VARCHAR(255) NOT NULL;  -- Fails if table has data
```

**Fix**: Three-step process (see "NOT NULL Column" above)

### Mistake 4: Breaking Foreign Keys

**Problem**:
```sql
DROP TABLE politicians;  -- Fails if speakers references it
```

**Fix**:
```sql
-- Drop foreign keys first
ALTER TABLE speakers DROP CONSTRAINT IF EXISTS fk_speakers_politicians;

-- Then drop table
DROP TABLE IF EXISTS politicians;
```

### Mistake 5: Wrong Data Types

**Problem**: Using wrong PostgreSQL types

**Fix**: Use appropriate types:
- `VARCHAR(n)` for short strings with known max length
- `TEXT` for long strings without limit
- `INTEGER` for whole numbers
- `NUMERIC(p,s)` for exact decimals
- `TIMESTAMP` for dates/times (not `DATETIME`)
- `JSONB` for JSON data (not `JSON`)

### Mistake 6: Missing Indexes

**Problem**: Slow queries due to missing indexes

**Fix**: Create indexes for:
- Foreign key columns (ALWAYS)
- Columns used in WHERE clauses
- Columns used in ORDER BY
- Columns used in JOIN conditions

### Mistake 7: Too Many Indexes

**Problem**: Over-indexing slows down writes

**Fix**: Only create indexes that will actually be used

## Testing Migrations

### Local Testing

```bash
# Test migration by resetting database
./reset-database.sh

# Check if table/column exists
docker compose -f docker/docker-compose.yml [-f docker/docker-compose.override.yml] exec postgres \
    psql -U polibase_user -d polibase_db \
    -c "\d table_name"

# Check column details
docker compose -f docker/docker-compose.yml [-f docker/docker-compose.override.yml] exec postgres \
    psql -U polibase_user -d polibase_db \
    -c "\d+ table_name"

# Check indexes
docker compose -f docker/docker-compose.yml [-f docker/docker-compose.override.yml] exec postgres \
    psql -U polibase_user -d polibase_db \
    -c "\di+ table_name*"
```

### Manual Application

```bash
# Apply single migration manually
cat database/migrations/XXX_migration.sql | \
    docker compose -f docker/docker-compose.yml [-f docker/docker-compose.override.yml] exec -T postgres \
    psql -U polibase_user -d polibase_db
```

### Rollback Strategy

**Polibase doesn't support automatic rollback**. Instead:

1. Create a new migration to undo changes
2. Never modify existing migrations once merged
3. Use `IF NOT EXISTS` / `IF EXISTS` for safety

## Schema Documentation

After creating migrations, update:

- `docs/DATABASE_SCHEMA.md` - Schema documentation
- Entity classes in `src/domain/entities/`
- Repository interfaces in `src/domain/repositories/`
- SQLAlchemy models in `src/infrastructure/persistence/models/`

## PostgreSQL-Specific Features

### JSONB

```sql
-- Store JSON data
ALTER TABLE table_name
    ADD COLUMN IF NOT EXISTS metadata JSONB;

-- Index on JSONB field
CREATE INDEX IF NOT EXISTS idx_table_metadata
    ON table_name USING GIN (metadata);

-- Query JSONB
SELECT * FROM table_name
WHERE metadata->>'key' = 'value';
```

### Arrays

```sql
-- Store arrays
ALTER TABLE table_name
    ADD COLUMN IF NOT EXISTS tags TEXT[];

-- Query arrays
SELECT * FROM table_name
WHERE 'tag1' = ANY(tags);
```

### Full Text Search

```sql
-- Add tsvector column
ALTER TABLE table_name
    ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- Update search vector
UPDATE table_name
SET search_vector = to_tsvector('japanese', name || ' ' || description);

-- Create GIN index for fast search
CREATE INDEX IF NOT EXISTS idx_table_search
    ON table_name USING GIN (search_vector);
```

## References

- PostgreSQL Documentation: https://www.postgresql.org/docs/
- Migration best practices: https://www.braintreepayments.com/blog/safe-operations-for-high-volume-postgresql/
- Database schema docs: `docs/DATABASE_SCHEMA.md`
