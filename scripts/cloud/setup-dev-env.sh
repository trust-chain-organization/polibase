#!/bin/bash
# GCP開発環境の起動スクリプト（GCSダンプからの復元）
set -e

PROJECT_ID="${GCP_PROJECT_ID:-trust-chain-828ad}"
REGION="${GCP_REGION:-asia-northeast1}"
INSTANCE_NAME="${CLOUD_SQL_INSTANCE:-polibase-dev-db}"
DATABASE_NAME="${DATABASE_NAME:-sagebase_db}"
DB_USER="${DB_USER:-sagebase_user}"
GCS_BUCKET="${GCS_BUCKET_NAME:-polibase-backups}"
BACKUP_FILE="database-snapshots/latest.sql"

echo "🚀 Starting Polibase development environment..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Cloud SQLインスタンスの存在確認
echo "📊 Checking Cloud SQL instance status..."
INSTANCE_EXISTS=$(gcloud sql instances list \
  --project="$PROJECT_ID" \
  --filter="name=$INSTANCE_NAME" \
  --format="value(name)" || echo "")

if [ -z "$INSTANCE_EXISTS" ]; then
  echo "❌ Cloud SQL instance not found. Creating new instance..."

  # バックアップの存在確認
  echo "🔍 Checking for backup in GCS..."
  BACKUP_EXISTS=$(gsutil ls "gs://$GCS_BUCKET/$BACKUP_FILE" 2>/dev/null || echo "")

  if [ -z "$BACKUP_EXISTS" ]; then
    echo "⚠️  No backup found at gs://$GCS_BUCKET/$BACKUP_FILE"
    echo "💡 This appears to be the first setup. Creating empty database..."
    CREATE_EMPTY=true
  else
    echo "✅ Backup found: gs://$GCS_BUCKET/$BACKUP_FILE"
    CREATE_EMPTY=false
  fi

  # Cloud SQLインスタンス作成
  echo "🏗️  Creating Cloud SQL instance (this takes 5-10 minutes)..."
  gcloud sql instances create "$INSTANCE_NAME" \
    --project="$PROJECT_ID" \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region="$REGION" \
    --storage-type=SSD \
    --storage-size=10GB \
    --storage-auto-increase \
    --backup-start-time=03:00 \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=4 \
    --quiet

  echo "⏳ Waiting for instance to be ready..."
  gcloud sql operations wait \
    $(gcloud sql operations list \
      --instance="$INSTANCE_NAME" \
      --project="$PROJECT_ID" \
      --limit=1 \
      --format="value(name)") \
    --project="$PROJECT_ID"

  # データベース作成
  echo "📁 Creating database..."
  gcloud sql databases create "$DATABASE_NAME" \
    --instance="$INSTANCE_NAME" \
    --project="$PROJECT_ID"

  # ユーザー設定
  echo "👤 Setting up database user..."
  DB_PASSWORD=$(openssl rand -base64 32)
  gcloud sql users create "$DB_USER" \
    --instance="$INSTANCE_NAME" \
    --password="$DB_PASSWORD" \
    --project="$PROJECT_ID"

  echo "🔑 Database password: $DB_PASSWORD"
  echo "💾 Save this password to your .env file"

  if [ "$CREATE_EMPTY" = false ]; then
    # バックアップから復元
    echo "📥 Importing data from GCS backup..."
    gcloud sql import sql "$INSTANCE_NAME" \
      "gs://$GCS_BUCKET/$BACKUP_FILE" \
      --database="$DATABASE_NAME" \
      --project="$PROJECT_ID" \
      --quiet

    echo "✅ Data restored from backup"
  else
    echo "💡 Empty database created. Run migrations to initialize schema."
  fi

else
  echo "✅ Cloud SQL instance already exists"

  # インスタンスの状態確認
  STATE=$(gcloud sql instances describe "$INSTANCE_NAME" \
    --project="$PROJECT_ID" \
    --format="value(state)")

  ACTIVATION_POLICY=$(gcloud sql instances describe "$INSTANCE_NAME" \
    --project="$PROJECT_ID" \
    --format="value(settings.activationPolicy)")

  echo "   State: $STATE"
  echo "   Activation Policy: $ACTIVATION_POLICY"

  if [ "$ACTIVATION_POLICY" = "NEVER" ]; then
    echo "🔄 Starting stopped instance..."
    gcloud sql instances patch "$INSTANCE_NAME" \
      --activation-policy=ALWAYS \
      --project="$PROJECT_ID" \
      --quiet

    echo "⏳ Waiting for instance to start..."
    sleep 30
  fi
fi

# 接続情報取得
echo ""
echo "📋 Connection Information:"
CONNECTION_NAME=$(gcloud sql instances describe "$INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --format="value(connectionName)")

IP_ADDRESS=$(gcloud sql instances describe "$INSTANCE_NAME" \
  --project="$PROJECT_ID" \
  --format="value(ipAddresses[0].ipAddress)")

echo "   Connection Name: $CONNECTION_NAME"
echo "   IP Address: $IP_ADDRESS"
echo "   Database: $DATABASE_NAME"
echo "   User: $DB_USER"
echo ""

# Cloud Run確認
echo "🌐 Checking Cloud Run services..."
SERVICES=$(gcloud run services list \
  --project="$PROJECT_ID" \
  --region="$REGION" \
  --format="value(metadata.name)" 2>/dev/null || echo "")

if [ -z "$SERVICES" ]; then
  echo "⚠️  No Cloud Run services deployed yet"
  echo "💡 Deploy services with: gcloud run deploy ..."
else
  echo "✅ Cloud Run services:"
  gcloud run services list \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --format="table(metadata.name,status.url,status.conditions[0].status)"
fi

echo ""
echo "✨ Development environment is ready!"
echo ""
echo "📝 Next steps:"
echo "   1. Update your .env file with the connection information"
echo "   2. Deploy Cloud Run services if not already deployed"
echo "   3. Access your application"
echo ""
echo "💡 To stop and save costs, run: ./scripts/cloud/teardown-dev-env.sh"
