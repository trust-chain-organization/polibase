#!/bin/bash
# Cloud Run用Dockerイメージのローカルテストスクリプト

set -e

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Cloud Run Docker Image Local Test ===${NC}"

# 変数設定
IMAGE_NAME="polibase-streamlit-cloudrun"
CONTAINER_NAME="polibase-cloudrun-test"
PORT=8080
HEALTH_PORT=8081

# 既存のコンテナを停止・削除
if docker ps -a | grep -q "$CONTAINER_NAME"; then
    echo -e "${YELLOW}Stopping and removing existing container...${NC}"
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
fi

# Dockerイメージのビルド
echo -e "${GREEN}Building Docker image...${NC}"
docker build -f Dockerfile.cloudrun -t "$IMAGE_NAME" .

# .envファイルの確認
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create .env file with required environment variables"
    exit 1
fi

# コンテナの起動
echo -e "${GREEN}Starting container...${NC}"
docker run -d \
    --name "$CONTAINER_NAME" \
    -p $PORT:$PORT \
    -p $HEALTH_PORT:$HEALTH_PORT \
    --env-file .env \
    -e PORT=$PORT \
    -e HEALTH_CHECK_PORT=$HEALTH_PORT \
    -e CLOUD_RUN=false \
    -e GOOGLE_OAUTH_DISABLED=true \
    "$IMAGE_NAME"

# コンテナが起動するまで待機
echo -e "${YELLOW}Waiting for container to start...${NC}"
sleep 5

# コンテナのログを表示
echo -e "${GREEN}Container logs:${NC}"
docker logs "$CONTAINER_NAME"

# ヘルスチェックの確認
echo -e "${GREEN}Checking health endpoints...${NC}"

MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s "http://localhost:$HEALTH_PORT/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Health check endpoint is responding${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -e "${YELLOW}Waiting for health endpoint... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗ Health check endpoint did not respond in time${NC}"
    docker logs "$CONTAINER_NAME"
    exit 1
fi

# ヘルスチェックレスポンスの確認
echo -e "${GREEN}Health check response:${NC}"
curl -s "http://localhost:$HEALTH_PORT/health" | jq . || curl -s "http://localhost:$HEALTH_PORT/health"

echo -e "${GREEN}Readiness check response:${NC}"
curl -s "http://localhost:$HEALTH_PORT/readiness" | jq . || curl -s "http://localhost:$HEALTH_PORT/readiness"

# Streamlitアプリの確認
echo -e "${GREEN}Checking Streamlit application...${NC}"

RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s "http://localhost:$PORT" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Streamlit application is responding${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -e "${YELLOW}Waiting for Streamlit... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗ Streamlit application did not respond in time${NC}"
    docker logs "$CONTAINER_NAME"
    exit 1
fi

echo -e "${GREEN}=== Test Summary ===${NC}"
echo -e "${GREEN}✓ Docker image built successfully${NC}"
echo -e "${GREEN}✓ Container started successfully${NC}"
echo -e "${GREEN}✓ Health check endpoint is working${NC}"
echo -e "${GREEN}✓ Streamlit application is accessible${NC}"
echo ""
echo -e "${GREEN}Access the application:${NC}"
echo -e "  Streamlit UI: ${YELLOW}http://localhost:$PORT${NC}"
echo -e "  Health check: ${YELLOW}http://localhost:$HEALTH_PORT/health${NC}"
echo -e "  Readiness check: ${YELLOW}http://localhost:$HEALTH_PORT/readiness${NC}"
echo ""
echo -e "${YELLOW}To view logs:${NC}"
echo "  docker logs -f $CONTAINER_NAME"
echo ""
echo -e "${YELLOW}To stop the container:${NC}"
echo "  docker stop $CONTAINER_NAME"
echo "  docker rm $CONTAINER_NAME"
