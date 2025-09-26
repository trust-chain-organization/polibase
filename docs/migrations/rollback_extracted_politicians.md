# ExtractedPoliticians Table Migration Rollback Procedures

## Overview
This document describes the rollback procedures for the extracted_politicians table migration (migrations 026 and 027).

## Migration Files
- `026_create_extracted_politicians_table.sql`: Creates the extracted_politicians table and indexes
- `027_migrate_existing_politicians.sql`: Migrates existing politicians data to extracted_politicians

## Rollback Procedures

### Method 1: Using Python Script
The safest method is to use the provided Python script:

```bash
# Verify migration status
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run python scripts/migrate_politicians_to_extracted.py --verify

# Rollback migration (removes migrated records)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run python scripts/migrate_politicians_to_extracted.py --rollback
```

### Method 2: Manual SQL Rollback

#### Step 1: Remove migrated data
```sql
-- Delete migrated records (approved status with no reviewer_id)
DELETE FROM extracted_politicians
WHERE status = 'approved'
  AND reviewer_id IS NULL;
```

#### Step 2: Drop the table and related objects
```sql
-- Drop trigger
DROP TRIGGER IF EXISTS update_extracted_politicians_updated_at ON extracted_politicians;

-- Drop indexes
DROP INDEX IF EXISTS idx_extracted_politicians_party_id;
DROP INDEX IF EXISTS idx_extracted_politicians_status;
DROP INDEX IF EXISTS idx_extracted_politicians_extracted_at;
DROP INDEX IF EXISTS idx_extracted_politicians_name_party;

-- Drop table
DROP TABLE IF EXISTS extracted_politicians;
```

## Data Integrity Verification

### Before Rollback
```sql
-- Count politicians
SELECT COUNT(*) as politician_count FROM politicians;

-- Count extracted politicians
SELECT
    status,
    COUNT(*) as count,
    COUNT(reviewer_id) as with_reviewer
FROM extracted_politicians
GROUP BY status;
```

### After Rollback
```sql
-- Verify politicians table is intact
SELECT COUNT(*) as politician_count FROM politicians;

-- Verify extracted_politicians is removed
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name = 'extracted_politicians'
) as table_exists;
```

## Recovery from Failed Rollback

If the rollback fails:

1. **Check transaction status**:
   ```sql
   SELECT * FROM pg_stat_activity
   WHERE state != 'idle'
     AND query LIKE '%extracted_politicians%';
   ```

2. **Kill blocking transactions if necessary**:
   ```sql
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state != 'idle'
     AND query LIKE '%extracted_politicians%';
   ```

3. **Restore from backup**:
   ```bash
   ./backup-database.sh restore database/backups/[pre-migration-backup]
   ```

## Important Notes

- **Always backup before rollback**: Create a backup before attempting any rollback procedure
- **Verify data counts**: Ensure no data loss by comparing record counts before and after
- **Test in development first**: Always test rollback procedures in a development environment
- **Migration is idempotent**: The migration scripts can be run multiple times safely due to existence checks
