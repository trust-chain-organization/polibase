#!/bin/bash
# Cloud RunへのStreamlitアプリケーションデプロイスクリプト

set -e

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Cloud Run Deployment Script ===${NC}"

# 環境変数の確認
check_env_var() {
    if [ -z "${!1}" ]; then
        echo -e "${RED}Error: $1 is not set${NC}"
        echo "Please set $1 environment variable"
        exit 1
    fi
}

# 必須環境変数の確認
echo -e "${YELLOW}Checking required environment variables...${NC}"
check_env_var "PROJECT_ID"
check_env_var "REGION"

# オプション変数のデフォルト値設定
SERVICE_NAME="${SERVICE_NAME:-polibase-streamlit}"
IMAGE_NAME="${IMAGE_NAME:-$SERVICE_NAME}"
REPOSITORY="${REPOSITORY:-polibase}"
TAG="${TAG:-latest}"

# Cloud SQL設定（オプション）
CLOUD_SQL_INSTANCE="${CLOUD_SQL_INSTANCE:-}"

echo -e "${GREEN}Deployment configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service Name: $SERVICE_NAME"
echo "  Image Name: $IMAGE_NAME"
echo "  Repository: $REPOSITORY"
echo "  Tag: $TAG"
[ -n "$CLOUD_SQL_INSTANCE" ] && echo "  Cloud SQL Instance: $CLOUD_SQL_INSTANCE"
echo ""

# GCPプロジェクトの設定
echo -e "${YELLOW}Setting GCP project...${NC}"
gcloud config set project "$PROJECT_ID"

# Artifact Registryリポジトリの確認/作成
echo -e "${YELLOW}Checking Artifact Registry repository...${NC}"
if ! gcloud artifacts repositories describe "$REPOSITORY" \
    --location="$REGION" \
    --project="$PROJECT_ID" > /dev/null 2>&1; then
    echo -e "${YELLOW}Creating Artifact Registry repository...${NC}"
    gcloud artifacts repositories create "$REPOSITORY" \
        --repository-format=docker \
        --location="$REGION" \
        --description="Polibase container images" \
        --project="$PROJECT_ID"
else
    echo -e "${GREEN}✓ Artifact Registry repository already exists${NC}"
fi

# Docker認証の設定
echo -e "${YELLOW}Configuring Docker authentication...${NC}"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# イメージのフルパス
IMAGE_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}"

# Dockerイメージのビルド
echo -e "${GREEN}Building Docker image...${NC}"
docker build -f Dockerfile.cloudrun -t "$IMAGE_PATH" .

# イメージのプッシュ
echo -e "${GREEN}Pushing image to Artifact Registry...${NC}"
docker push "$IMAGE_PATH"

# Cloud Runサービスのデプロイ
echo -e "${GREEN}Deploying to Cloud Run...${NC}"

DEPLOY_ARGS=(
    "run"
    "deploy"
    "$SERVICE_NAME"
    "--image=$IMAGE_PATH"
    "--region=$REGION"
    "--platform=managed"
    "--allow-unauthenticated"
    "--port=8080"
    "--cpu=2"
    "--memory=2Gi"
    "--timeout=300"
    "--max-instances=10"
    "--min-instances=0"
    "--set-env-vars=CLOUD_RUN=true"
    "--set-env-vars=PORT=8080"
    "--set-env-vars=HEALTH_CHECK_PORT=8081"
    "--set-env-vars=LOG_LEVEL=INFO"
    "--project=$PROJECT_ID"
)

# Secret Managerからのシークレット設定
if gcloud secrets describe google-api-key --project="$PROJECT_ID" > /dev/null 2>&1; then
    echo -e "${YELLOW}Setting secrets from Secret Manager...${NC}"
    DEPLOY_ARGS+=("--set-secrets=GOOGLE_API_KEY=google-api-key:latest")
fi

if gcloud secrets describe database-password --project="$PROJECT_ID" > /dev/null 2>&1; then
    DEPLOY_ARGS+=("--set-secrets=DB_PASSWORD=database-password:latest")
fi

# Cloud SQL接続設定
if [ -n "$CLOUD_SQL_INSTANCE" ]; then
    echo -e "${YELLOW}Configuring Cloud SQL connection...${NC}"
    DEPLOY_ARGS+=("--add-cloudsql-instances=$CLOUD_SQL_INSTANCE")
    DEPLOY_ARGS+=("--set-env-vars=USE_CLOUD_SQL_PROXY=true")
    DEPLOY_ARGS+=("--set-env-vars=CLOUD_SQL_CONNECTION_NAME=$CLOUD_SQL_INSTANCE")
    DEPLOY_ARGS+=("--set-env-vars=CLOUD_SQL_UNIX_SOCKET_DIR=/cloudsql")
    DEPLOY_ARGS+=("--set-env-vars=DB_USER=sagebase_user")
    DEPLOY_ARGS+=("--set-env-vars=DB_NAME=sagebase_db")
fi

# ヘルスチェック設定
DEPLOY_ARGS+=(
    "--no-cpu-throttling"
)

# デプロイ実行
gcloud "${DEPLOY_ARGS[@]}"

# デプロイ結果の確認
echo -e "${GREEN}Checking deployment status...${NC}"
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format="value(status.url)")

echo ""
echo -e "${GREEN}=== Deployment Successful! ===${NC}"
echo -e "Service URL: ${YELLOW}$SERVICE_URL${NC}"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Verify health check: curl ${SERVICE_URL%/}:8081/health"
echo "2. Access the application: $SERVICE_URL"
echo "3. View logs: gcloud run logs tail $SERVICE_NAME --region=$REGION --project=$PROJECT_ID"
echo ""
echo -e "${YELLOW}Deployment commands for future reference:${NC}"
echo "  Update service: gcloud run services update $SERVICE_NAME --region=$REGION --project=$PROJECT_ID"
echo "  View service: gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID"
echo "  Delete service: gcloud run services delete $SERVICE_NAME --region=$REGION --project=$PROJECT_ID"
