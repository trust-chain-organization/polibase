#!/bin/bash
# GCP開発環境の停止・削除スクリプト（GCSへのバックアップ）
set -e

PROJECT_ID="${GCP_PROJECT_ID:-trust-chain-828ad}"
REGION="${GCP_REGION:-asia-northeast1}"
INSTANCE_NAME="${CLOUD_SQL_INSTANCE:-sagebase-dev-db}"
DATABASE_NAME="${DATABASE_NAME:-sagebase_db}"
GCS_BUCKET="${GCS_BUCKET_NAME:-sagebase-backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "🛑 Stopping Sagebase development environment..."
echo "Project: $PROJECT_ID"
echo ""

# Cloud SQLインスタンスの存在確認
INSTANCE_EXISTS=$(gcloud sql instances list \
  --project="$PROJECT_ID" \
  --filter="name=$INSTANCE_NAME" \
  --format="value(name)" || echo "")

if [ -z "$INSTANCE_EXISTS" ]; then
  echo "⚠️  Cloud SQL instance not found. Nothing to stop."
  exit 0
fi

echo "📊 Current instance status:"
gcloud sql instances describe "$INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --format="table(name,state,settings.activationPolicy,databaseVersion)"

echo ""
read -p "Do you want to backup and delete this instance? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "❌ Cancelled. No changes made."
  exit 0
fi

# バックアップ作成
echo "💾 Creating backup to GCS..."
BACKUP_FILE="database-snapshots/backup_${TIMESTAMP}.sql"

echo "   Exporting to: gs://$GCS_BUCKET/$BACKUP_FILE"
gcloud sql export sql "$INSTANCE_NAME" \
  "gs://$GCS_BUCKET/$BACKUP_FILE" \
  --database="$DATABASE_NAME" \
  --project="$PROJECT_ID" \
  --offload

echo "✅ Backup completed"

# 最新バックアップのシンボリックリンク作成（GCSコピー）
echo "🔗 Updating latest backup reference..."
gsutil cp "gs://$GCS_BUCKET/$BACKUP_FILE" \
  "gs://$GCS_BUCKET/database-snapshots/latest.sql"

echo "✅ Latest backup updated"

# バックアップ情報を保存
BACKUP_INFO="database-snapshots/backup_info_${TIMESTAMP}.json"
cat > /tmp/backup_info.json <<EOF
{
  "timestamp": "$TIMESTAMP",
  "instance_name": "$INSTANCE_NAME",
  "database_name": "$DATABASE_NAME",
  "backup_file": "$BACKUP_FILE",
  "backup_size": "$(gsutil du -s gs://$GCS_BUCKET/$BACKUP_FILE | awk '{print $1}')",
  "instance_tier": "$(gcloud sql instances describe $INSTANCE_NAME --project=$PROJECT_ID --format='value(settings.tier)')"
}
EOF
gsutil cp /tmp/backup_info.json "gs://$GCS_BUCKET/$BACKUP_INFO"
rm /tmp/backup_info.json

# インスタンス削除
echo ""
echo "🗑️  Deleting Cloud SQL instance..."
read -p "Are you sure? This will delete the instance (backup is saved). (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "❌ Cancelled. Instance not deleted."
  exit 0
fi

gcloud sql instances delete "$INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --quiet

echo "✅ Cloud SQL instance deleted"

echo ""
echo "💤 Development environment stopped"
echo ""
echo "📊 Cost savings:"
echo "   Before: ~$150/month (db-custom-2-8192) or ~$15/month (db-f1-micro)"
echo "   After:  ~$0.02/month (GCS storage only)"
echo ""
echo "📁 Backups saved in GCS:"
echo "   Latest: gs://$GCS_BUCKET/database-snapshots/latest.sql"
echo "   Timestamped: gs://$GCS_BUCKET/$BACKUP_FILE"
echo ""
echo "🔄 To restore, run: ./scripts/cloud/setup-dev-env.sh"
echo ""
echo "📋 Backup list:"
gsutil ls -lh "gs://$GCS_BUCKET/database-snapshots/"
