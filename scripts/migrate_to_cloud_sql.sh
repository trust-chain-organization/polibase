#!/bin/bash
# Local PostgreSQLからCloud SQLへのデータベース移行スクリプト

set -e

# カラー出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🚀 Cloud SQL データベース移行ツール"
echo "========================================"
echo ""

# 設定の読み込み
if [ -f .env ]; then
    source .env
else
    echo -e "${RED}❌ .envファイルが見つかりません${NC}"
    exit 1
fi

# 必要な環境変数の確認
CLOUD_SQL_CONNECTION_NAME="${CLOUD_SQL_CONNECTION_NAME:-}"
GCP_PROJECT_ID="${GCP_PROJECT_ID:-}"
CLOUD_SQL_INSTANCE="${CLOUD_SQL_INSTANCE:-}"

if [ -z "$CLOUD_SQL_CONNECTION_NAME" ] && [ -z "$CLOUD_SQL_INSTANCE" ]; then
    echo -e "${RED}❌ CLOUD_SQL_CONNECTION_NAME または CLOUD_SQL_INSTANCE が設定されていません${NC}"
    exit 1
fi

# Cloud SQL接続名からインスタンス名を抽出（CONNECTION_NAMEがある場合）
if [ -n "$CLOUD_SQL_CONNECTION_NAME" ]; then
    IFS=':' read -r PROJECT_ID REGION INSTANCE_NAME <<< "$CLOUD_SQL_CONNECTION_NAME"
    GCP_PROJECT_ID="${GCP_PROJECT_ID:-$PROJECT_ID}"
    CLOUD_SQL_INSTANCE="${CLOUD_SQL_INSTANCE:-$INSTANCE_NAME}"
fi

# データベース設定
DB_NAME="${DB_NAME:-sagebase_db}"
DB_USER="${DB_USER:-sagebase_user}"
BACKUP_DIR="./tmp/db_migration_$(date +%Y%m%d_%H%M%S)"

echo -e "${BLUE}📋 移行設定:${NC}"
echo "   GCPプロジェクトID: $GCP_PROJECT_ID"
echo "   Cloud SQLインスタンス: $CLOUD_SQL_INSTANCE"
echo "   データベース名: $DB_NAME"
echo "   バックアップディレクトリ: $BACKUP_DIR"
echo ""

# 確認
echo -e "${YELLOW}⚠️  この操作は以下を実行します:${NC}"
echo "   1. ローカルPostgreSQLからデータをエクスポート"
echo "   2. Cloud SQLインスタンスの存在確認"
echo "   3. Cloud SQLへスキーマとデータをインポート"
echo "   4. 接続テストの実行"
echo ""
read -p "続行しますか？ (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}❌ 移行をキャンセルしました${NC}"
    exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 1: ローカルデータベースのエクスポート
echo -e "${BLUE}📦 Step 1: ローカルデータベースのエクスポート${NC}"
echo ""

mkdir -p "$BACKUP_DIR"

# Dockerコンテナからエクスポート
echo "   ローカルPostgreSQLからデータをエクスポート中..."
docker exec docker-postgres-1 pg_dump -U "$DB_USER" -d "$DB_NAME" --clean --if-exists > "$BACKUP_DIR/database_export.sql"

if [ $? -eq 0 ]; then
    EXPORT_SIZE=$(du -h "$BACKUP_DIR/database_export.sql" | cut -f1)
    echo -e "${GREEN}   ✅ エクスポート完了 (サイズ: $EXPORT_SIZE)${NC}"
    echo "      ファイル: $BACKUP_DIR/database_export.sql"
else
    echo -e "${RED}   ❌ エクスポートに失敗しました${NC}"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 2: Cloud SQLインスタンスの確認
echo -e "${BLUE}📊 Step 2: Cloud SQLインスタンスの確認${NC}"
echo ""

INSTANCE_EXISTS=$(gcloud sql instances list \
    --project="$GCP_PROJECT_ID" \
    --filter="name=$CLOUD_SQL_INSTANCE" \
    --format="value(name)" 2>/dev/null || echo "")

if [ -z "$INSTANCE_EXISTS" ]; then
    echo -e "${YELLOW}   ⚠️  Cloud SQLインスタンスが見つかりません${NC}"
    echo ""
    echo "   Terraformでインスタンスを作成してください:"
    echo "   cd terraform"
    echo "   terraform apply"
    echo ""
    read -p "   Terraformを実行しますか？ (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -f terraform/main.tf ]; then
            cd terraform
            terraform init
            terraform apply
            cd ..
        else
            echo -e "${RED}   ❌ terraform/main.tf が見つかりません${NC}"
            exit 1
        fi
    else
        echo -e "${RED}   ❌ Cloud SQLインスタンスが必要です${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}   ✅ Cloud SQLインスタンスが見つかりました: $CLOUD_SQL_INSTANCE${NC}"

    # インスタンスの状態確認
    STATE=$(gcloud sql instances describe "$CLOUD_SQL_INSTANCE" \
        --project="$GCP_PROJECT_ID" \
        --format="value(state)")
    echo "      状態: $STATE"

    if [ "$STATE" != "RUNNABLE" ]; then
        echo -e "${YELLOW}   ⚠️  インスタンスが実行中ではありません${NC}"
        exit 1
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 3: GCSへのアップロード（Cloud SQLのインポートはGCS経由のみ）
echo -e "${BLUE}☁️  Step 3: GCSへのバックアップアップロード${NC}"
echo ""

GCS_BUCKET="${GCS_BUCKET_NAME:-polibase-backups}"
GCS_PATH="gs://$GCS_BUCKET/database-migrations/migration_$(date +%Y%m%d_%H%M%S).sql"

echo "   GCSバケット: $GCS_BUCKET"
echo "   アップロード先: $GCS_PATH"

# バケットの存在確認
if ! gsutil ls -b "gs://$GCS_BUCKET" &>/dev/null; then
    echo -e "${YELLOW}   ⚠️  GCSバケットが見つかりません。作成します...${NC}"
    gsutil mb -p "$GCP_PROJECT_ID" -c STANDARD -l asia-northeast1 "gs://$GCS_BUCKET"
fi

echo "   ファイルをアップロード中..."
gsutil cp "$BACKUP_DIR/database_export.sql" "$GCS_PATH"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}   ✅ アップロード完了${NC}"
else
    echo -e "${RED}   ❌ アップロードに失敗しました${NC}"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 4: Cloud SQLへのインポート
echo -e "${BLUE}📥 Step 4: Cloud SQLへのインポート${NC}"
echo ""

echo -e "${YELLOW}   ⚠️  既存のデータは削除されます (--clean オプション)${NC}"
read -p "   インポートを実行しますか？ (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}   ℹ️  インポートをスキップしました${NC}"
    echo "      手動でインポートする場合:"
    echo "      gcloud sql import sql $CLOUD_SQL_INSTANCE $GCS_PATH --database=$DB_NAME --project=$GCP_PROJECT_ID"
else
    echo "   Cloud SQLへインポート中..."
    gcloud sql import sql "$CLOUD_SQL_INSTANCE" "$GCS_PATH" \
        --database="$DB_NAME" \
        --project="$GCP_PROJECT_ID" \
        --quiet

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}   ✅ インポート完了${NC}"
    else
        echo -e "${RED}   ❌ インポートに失敗しました${NC}"
        echo "      ログを確認してください:"
        echo "      gcloud sql operations list --instance=$CLOUD_SQL_INSTANCE --project=$GCP_PROJECT_ID"
        exit 1
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 5: 接続テスト
echo -e "${BLUE}🔍 Step 5: Cloud SQL接続テスト${NC}"
echo ""

echo "   Cloud SQL Proxyのセットアップを確認..."

if [ -f scripts/cloud_sql_proxy_setup.sh ]; then
    echo "   Cloud SQL Proxyをセットアップするには:"
    echo "   ./scripts/cloud_sql_proxy_setup.sh"
    echo ""
    read -p "   今すぐセットアップしますか？ (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ./scripts/cloud_sql_proxy_setup.sh
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}✨ 移行完了！${NC}"
echo ""
echo "📝 次のステップ:"
echo "   1. .envファイルを更新:"
echo "      USE_CLOUD_SQL_PROXY=true"
echo "      CLOUD_SQL_CONNECTION_NAME=$CLOUD_SQL_CONNECTION_NAME"
echo ""
echo "   2. Cloud SQL Proxyを起動:"
echo "      ./scripts/cloud_sql_proxy_setup.sh"
echo ""
echo "   3. アプリケーションで接続テスト:"
echo "      python -m src.infrastructure.config.database"
echo ""
echo "   4. アプリケーションを起動:"
echo "      just streamlit"
echo ""
echo "💾 バックアップファイル:"
echo "   ローカル: $BACKUP_DIR/database_export.sql"
echo "   GCS: $GCS_PATH"
echo ""
