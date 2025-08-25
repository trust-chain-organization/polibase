# デプロイメントガイド

## 目次
- [環境構成](#環境構成)
- [Docker運用](#docker運用)
- [環境変数設定](#環境変数設定)
- [デプロイ手順](#デプロイ手順)
- [CI/CD設定](#cicd設定)
- [監視とログ](#監視とログ)

## 環境構成

### 環境一覧

| 環境 | 用途 | URL | デプロイ方法 |
|------|------|-----|-------------|
| Development | 開発 | http://localhost:8501 | Docker Compose |
| Staging | 検証 | https://staging.polibase.jp | 手動デプロイ |
| Production | 本番 | https://polibase.jp | GitHub Actions |

### インフラ構成

```
┌─────────────────────────────────────────┐
│           ロードバランサー                │
└─────────────────────────────────────────┘
                    │
    ┌───────────────┴───────────────┐
    ▼                               ▼
┌──────────┐                  ┌──────────┐
│  App #1  │                  │  App #2  │
│ (Docker) │                  │ (Docker) │
└──────────┘                  └──────────┘
    │                               │
    └───────────────┬───────────────┘
                    ▼
            ┌──────────────┐
            │  PostgreSQL  │
            │   (Managed)  │
            └──────────────┘
                    │
            ┌──────────────┐
            │     GCS      │
            │  (Storage)   │
            └──────────────┘
```

## Docker運用

### Dockerイメージ構成

```dockerfile
# Dockerfile
FROM python:3.11-slim

# 必要なシステムパッケージをインストール
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# UVのインストール
RUN pip install uv

# アプリケーションコードをコピー
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

# 実行コマンド
CMD ["uv", "run", "polibase", "streamlit"]
```

### Docker Compose設定

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  polibase:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - GCS_BUCKET_NAME=${GCS_BUCKET_NAME}
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=${DB_NAME}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

volumes:
  postgres_data:
```

### イメージビルドとプッシュ

```bash
# イメージビルド
docker build -t polibase:latest -f docker/Dockerfile .

# タグ付け
docker tag polibase:latest gcr.io/project-id/polibase:v1.0.0

# レジストリへプッシュ
docker push gcr.io/project-id/polibase:v1.0.0
```

## 環境変数設定

### 必須環境変数

```bash
# .env.production
# データベース
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Google API
GOOGLE_API_KEY=your-google-api-key

# Google Cloud Storage
GCS_BUCKET_NAME=polibase-production
GCS_UPLOAD_ENABLED=true

# アプリケーション設定
APP_ENV=production
LOG_LEVEL=INFO
```

### 環境別設定

```python
# src/config/settings.py
import os
from typing import Literal

class Settings:
    """環境設定クラス"""

    def __init__(self):
        self.env: Literal["development", "staging", "production"] = (
            os.getenv("APP_ENV", "development")
        )
        self.database_url = os.getenv("DATABASE_URL")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.gcs_bucket_name = os.getenv("GCS_BUCKET_NAME")

        # 環境別設定
        if self.env == "production":
            self.debug = False
            self.log_level = "INFO"
        else:
            self.debug = True
            self.log_level = "DEBUG"

settings = Settings()
```

## デプロイ手順

### 手動デプロイ

```bash
# 1. SSHでサーバーに接続
ssh user@server

# 2. 最新コードを取得
cd /app/polibase
git pull origin main

# 3. 環境変数を設定
cp .env.production .env

# 4. Dockerイメージを更新
docker compose pull

# 5. サービスを再起動
docker compose down
docker compose up -d

# 6. マイグレーション実行
docker compose exec polibase uv run alembic upgrade head

# 7. ヘルスチェック
curl http://localhost:8501/health
```

### ゼロダウンタイムデプロイ

```bash
#!/bin/bash
# deploy.sh

# Blue-Greenデプロイメント
CURRENT_COLOR=$(docker compose ps | grep green && echo "green" || echo "blue")
NEW_COLOR=$([[ $CURRENT_COLOR == "blue" ]] && echo "green" || echo "blue")

echo "Deploying to $NEW_COLOR environment..."

# 新環境を起動
docker compose -f docker-compose.$NEW_COLOR.yml up -d

# ヘルスチェック
for i in {1..30}; do
    if curl -f http://localhost:850$([[ $NEW_COLOR == "blue" ]] && echo "1" || echo "2")/health; then
        echo "Health check passed"
        break
    fi
    sleep 10
done

# ロードバランサーを切り替え
./switch-lb.sh $NEW_COLOR

# 旧環境を停止
sleep 30
docker compose -f docker-compose.$CURRENT_COLOR.yml down
```

## CI/CD設定

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  deploy:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/tags/')

    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to GCR
        uses: docker/login-action@v2
        with:
          registry: gcr.io
          username: _json_key
          password: ${{ secrets.GCP_SA_KEY }}

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          file: docker/Dockerfile
          push: true
          tags: |
            gcr.io/${{ secrets.GCP_PROJECT }}/polibase:latest
            gcr.io/${{ secrets.GCP_PROJECT }}/polibase:${{ github.sha }}

      - name: Deploy to Cloud Run
        if: github.ref == 'refs/heads/main'
        run: |
          echo "${{ secrets.GCP_SA_KEY }}" | base64 -d > key.json
          gcloud auth activate-service-account --key-file=key.json
          gcloud run deploy polibase \
            --image gcr.io/${{ secrets.GCP_PROJECT }}/polibase:${{ github.sha }} \
            --platform managed \
            --region asia-northeast1 \
            --allow-unauthenticated
```

### データベースマイグレーション

```bash
#!/bin/bash
# migrate.sh

# バックアップ作成
docker compose exec polibase uv run polibase database backup

# マイグレーション実行
docker compose exec polibase cat database/migrations/latest.sql | \
  docker compose exec -T postgres psql -U $DB_USER -d $DB_NAME

# 検証
docker compose exec polibase python -c "
from src.config.database import test_connection
test_connection()
"
```

## 監視とログ

### ヘルスチェック

```python
# src/interfaces/web/health.py
from fastapi import FastAPI
from sqlalchemy import text

app = FastAPI()

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    try:
        # データベース接続確認
        async with get_session() as session:
            await session.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
            "version": get_version()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }, 503
```

### ログ設定

```python
# src/utils/logger.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """JSON形式のログフォーマッター"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/var/log/polibase/app.log")
    ]
)

# JSON形式を適用
for handler in logging.root.handlers:
    handler.setFormatter(JSONFormatter())
```

### メトリクス収集

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

## バックアップとリカバリー

### 自動バックアップ

```yaml
# .github/workflows/backup.yml
name: Daily Backup

on:
  schedule:
    - cron: '0 2 * * *'  # 毎日2:00 UTC

jobs:
  backup:
    runs-on: ubuntu-latest

    steps:
      - name: Backup Database
        run: |
          pg_dump ${{ secrets.DATABASE_URL }} | \
            gsutil cp - gs://polibase-backups/$(date +%Y%m%d).sql.gz
```

### リストア手順

```bash
# 最新バックアップからリストア
gsutil cp gs://polibase-backups/latest.sql.gz - | \
  gunzip | \
  psql $DATABASE_URL
```

## セキュリティ設定

### SSL/TLS設定

```yaml
# nginx.conf
server {
    listen 443 ssl http2;
    server_name polibase.jp;

    ssl_certificate /etc/ssl/certs/polibase.crt;
    ssl_certificate_key /etc/ssl/private/polibase.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### ファイアウォール設定

```bash
# UFW設定
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 443/tcp
ufw allow 80/tcp
ufw enable
```

## トラブルシューティング

### デプロイ失敗時の対処

```bash
# ロールバック
docker compose down
git checkout HEAD~1
docker compose up -d

# ログ確認
docker compose logs -f polibase

# コンテナに入って調査
docker compose exec polibase bash
```

## 関連ドキュメント

- [開発ガイド](./development.md)
- [テストガイド](./testing.md)
- [CI/CDガイド](../CI_CD_ENHANCEMENTS.md)
- [トラブルシューティング](../troubleshooting/README.md)
