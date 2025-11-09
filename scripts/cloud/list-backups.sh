#!/bin/bash
# GCSに保存されたバックアップ一覧を表示
set -e

GCS_BUCKET="${GCS_BUCKET_NAME:-sagebase-backups}"

echo "📋 Cloud SQL Backups in GCS"
echo "Bucket: gs://$GCS_BUCKET/database-snapshots/"
echo ""

# バックアップファイル一覧
echo "Available backups:"
gsutil ls -lh "gs://$GCS_BUCKET/database-snapshots/*.sql" 2>/dev/null || {
  echo "No backups found."
  exit 0
}

echo ""
echo "Backup information files:"
gsutil ls -lh "gs://$GCS_BUCKET/database-snapshots/*.json" 2>/dev/null || true

echo ""
echo "💡 To restore from a specific backup:"
echo "   1. Edit scripts/cloud/setup-dev-env.sh"
echo "   2. Change BACKUP_FILE to the desired backup filename"
echo "   3. Run: ./scripts/cloud/setup-dev-env.sh"
