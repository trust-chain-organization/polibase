# Deployment Guide

このドキュメントは、Polibaseアプリケーションをクラウド環境（特にGoogle Cloud Platform）にデプロイする方法を説明します。

## 目次

- [Cloud SQL セットアップ](#cloud-sql-セットアップ)
- [ローカル開発環境からのCloud SQL接続](#ローカル開発環境からのcloud-sql接続)
- [データベース移行](#データベース移行)
- [Cloud Run デプロイ](#cloud-run-デプロイ)
- [Secret Manager 設定](#secret-manager-設定)
- [バックアップと復元](#バックアップと復元)
- [トラブルシューティング](#トラブルシューティング)

---

## Cloud SQL セットアップ

### 前提条件

1. Google Cloud Platform（GCP）プロジェクトが作成されている
2. gcloud CLIがインストールされている
3. Terraformがインストールされている（v1.0以降）
4. 適切な権限（Cloud SQL管理者、Secret Manager管理者など）

### 1. Terraformによるインフラ構築

PolibaseのCloud SQLインフラはTerraformで管理されています。

```bash
cd terraform

# 初回のみ：Terraformを初期化
terraform init

# 変数ファイルを作成
cp terraform.tfvars.example terraform.tfvars

# terraform.tfvarsを編集
# 必要な変数を設定：
# - project_id: GCPプロジェクトID
# - region: デプロイ先リージョン（デフォルト: asia-northeast1）
# - database_password: データベースパスワード（Secret Managerで管理を推奨）
# - google_api_key: Google API Key (Gemini)

# プランの確認
terraform plan

# 適用
terraform apply
```

作成されるリソース：

- **Cloud SQL インスタンス**: PostgreSQL 15
- **データベース**: polibase_db
- **データベースユーザー**: polibase_user
- **VPCネットワーク**: プライベートIP接続用
- **Secret Manager**: API キーとパスワードの保存
- **バックアップ設定**: 自動バックアップ（7日間保持）

### 2. Cloud SQLインスタンスの確認

```bash
# インスタンス一覧
gcloud sql instances list --project=YOUR_PROJECT_ID

# インスタンスの詳細確認
gcloud sql instances describe INSTANCE_NAME --project=YOUR_PROJECT_ID

# 接続名の取得
gcloud sql instances describe INSTANCE_NAME \
  --project=YOUR_PROJECT_ID \
  --format='value(connectionName)'
```

---

## ローカル開発環境からのCloud SQL接続

ローカル開発環境からCloud SQLに接続するには、**Cloud SQL Auth Proxy**を使用します。

### Cloud SQL Auth Proxyのセットアップ

自動セットアップスクリプトを使用：

```bash
./scripts/cloud_sql_proxy_setup.sh
```

このスクリプトは以下を実行します：

1. Cloud SQL Auth Proxyのダウンロードとインストール
2. 環境変数の確認
3. GCP認証の確認
4. Unixソケットディレクトリの準備
5. Cloud SQL Auth Proxyの起動（オプション）

### 手動セットアップ

1. **Cloud SQL Auth Proxyのダウンロード**

```bash
# macOS (Intel)
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.darwin.amd64

# macOS (Apple Silicon)
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.darwin.arm64

# Linux
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.linux.amd64

chmod +x cloud-sql-proxy
```

2. **GCP認証**

```bash
gcloud auth application-default login
```

3. **.envファイルの設定**

```bash
# Cloud SQL接続設定
CLOUD_SQL_CONNECTION_NAME=PROJECT_ID:REGION:INSTANCE_NAME
USE_CLOUD_SQL_PROXY=true
CLOUD_SQL_UNIX_SOCKET_DIR=/cloudsql

# データベース認証情報
DB_USER=polibase_user
DB_PASSWORD=YOUR_PASSWORD
DB_NAME=polibase_db
```

4. **Cloud SQL Auth Proxyの起動**

```bash
# Unixソケット接続（推奨）
mkdir -p /cloudsql
./cloud-sql-proxy --unix-socket=/cloudsql PROJECT_ID:REGION:INSTANCE_NAME

# TCP接続（代替方法）
# ./cloud-sql-proxy --port=5433 PROJECT_ID:REGION:INSTANCE_NAME
# DATABASE_URL=postgresql://polibase_user:password@localhost:5433/polibase_db
```

### 接続テスト

```bash
# Pythonスクリプトで接続テスト
python -m src.infrastructure.config.database

# psqlで直接接続（Unixソケット）
psql "host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME user=polibase_user dbname=polibase_db"
```

---

## データベース移行

ローカルのPostgreSQLデータベースからCloud SQLへデータを移行します。

### 自動移行スクリプト

```bash
./scripts/migrate_to_cloud_sql.sh
```

このスクリプトは以下を実行します：

1. ローカルPostgreSQLからデータエクスポート
2. Cloud SQLインスタンスの確認
3. GCSへのバックアップアップロード
4. Cloud SQLへのインポート
5. 接続テストのセットアップ

### 手動移行手順

#### 1. ローカルデータベースのエクスポート

```bash
# Dockerコンテナからエクスポート
docker exec docker-postgres-1 pg_dump \
  -U polibase_user \
  -d polibase_db \
  --clean --if-exists \
  > backup.sql
```

#### 2. GCSへのアップロード

```bash
# GCSバケット作成（初回のみ）
gsutil mb -p YOUR_PROJECT_ID -c STANDARD -l asia-northeast1 gs://polibase-backups

# バックアップをアップロード
gsutil cp backup.sql gs://polibase-backups/migrations/backup_$(date +%Y%m%d).sql
```

#### 3. Cloud SQLへのインポート

```bash
gcloud sql import sql INSTANCE_NAME \
  gs://polibase-backups/migrations/backup_YYYYMMDD.sql \
  --database=polibase_db \
  --project=YOUR_PROJECT_ID
```

#### 4. インポート確認

```bash
# Cloud SQL Proxyを起動
./cloud-sql-proxy --unix-socket=/cloudsql PROJECT_ID:REGION:INSTANCE_NAME

# psqlで接続して確認
psql "host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME user=polibase_user dbname=polibase_db"

# テーブル一覧
\dt

# データ確認
SELECT COUNT(*) FROM meetings;
SELECT COUNT(*) FROM politicians;
```

---

## Cloud Run デプロイ

### 1. コンテナイメージのビルド

```bash
# Artifact Registryリポジトリの作成（初回のみ）
gcloud artifacts repositories create polibase \
  --repository-format=docker \
  --location=asia-northeast1 \
  --project=YOUR_PROJECT_ID

# Dockerイメージのビルドとプッシュ
docker build -t asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/polibase/streamlit-ui:latest .
docker push asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/polibase/streamlit-ui:latest
```

### 2. Cloud Runサービスのデプロイ

```bash
gcloud run deploy polibase-ui \
  --image=asia-northeast1-docker.pkg.dev/YOUR_PROJECT_ID/polibase/streamlit-ui:latest \
  --region=asia-northeast1 \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="USE_CLOUD_SQL_PROXY=true" \
  --set-env-vars="CLOUD_SQL_CONNECTION_NAME=PROJECT_ID:REGION:INSTANCE_NAME" \
  --set-secrets="GOOGLE_API_KEY=google-api-key:latest" \
  --set-secrets="DB_PASSWORD=database-password:latest" \
  --add-cloudsql-instances=PROJECT_ID:REGION:INSTANCE_NAME \
  --project=YOUR_PROJECT_ID
```

**重要**: Cloud RunからCloud SQLへの接続は、`--add-cloudsql-instances`フラグで自動的にCloud SQL Proxyが設定されます。

---

## Secret Manager 設定

機密情報はSecret Managerで管理します。

### シークレットの作成

```bash
# Google API Key
echo -n "YOUR_GOOGLE_API_KEY" | gcloud secrets create google-api-key \
  --data-file=- \
  --replication-policy=automatic \
  --project=YOUR_PROJECT_ID

# データベースパスワード
echo -n "YOUR_DB_PASSWORD" | gcloud secrets create database-password \
  --data-file=- \
  --replication-policy=automatic \
  --project=YOUR_PROJECT_ID

# Sentry DSN（オプション）
echo -n "YOUR_SENTRY_DSN" | gcloud secrets create sentry-dsn \
  --data-file=- \
  --replication-policy=automatic \
  --project=YOUR_PROJECT_ID
```

### シークレットの使用

Terraformでは`terraform/modules/security/main.tf`でSecret Managerを管理しています。

Cloud Runでシークレットを使用：

```bash
gcloud run services update polibase-ui \
  --set-secrets="GOOGLE_API_KEY=google-api-key:latest" \
  --set-secrets="DB_PASSWORD=database-password:latest" \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID
```

---

## バックアップと復元

### 自動バックアップ

Cloud SQLの自動バックアップはTerraformで設定済み：

- **バックアップ時間**: 毎日 3:00 AM JST
- **保持期間**: 7日間
- **Point-in-Time Recovery**: 有効

```bash
# バックアップ一覧
gcloud sql backups list --instance=INSTANCE_NAME --project=YOUR_PROJECT_ID

# バックアップからの復元
gcloud sql backups restore BACKUP_ID \
  --backup-instance=SOURCE_INSTANCE \
  --backup-id=BACKUP_ID \
  --project=YOUR_PROJECT_ID
```

### 手動バックアップ

```bash
# オンデマンドバックアップ
gcloud sql backups create --instance=INSTANCE_NAME --project=YOUR_PROJECT_ID

# GCSへのエクスポート（推奨）
gcloud sql export sql INSTANCE_NAME \
  gs://polibase-backups/manual-backups/backup_$(date +%Y%m%d_%H%M%S).sql \
  --database=polibase_db \
  --project=YOUR_PROJECT_ID
```

### Point-in-Time Recovery

```bash
# 特定の時刻に復元
gcloud sql instances clone SOURCE_INSTANCE TARGET_INSTANCE \
  --point-in-time='2024-01-15T10:00:00.000Z' \
  --project=YOUR_PROJECT_ID
```

---

## トラブルシューティング

### Cloud SQL Proxyが接続できない

**症状**: `connection refused` または `permission denied`

**解決方法**:

1. GCP認証を確認

```bash
gcloud auth application-default login
gcloud auth application-default print-access-token
```

2. Cloud SQL Admin APIが有効か確認

```bash
gcloud services enable sqladmin.googleapis.com --project=YOUR_PROJECT_ID
```

3. IAM権限を確認（Cloud SQL Client ロールが必要）

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:YOUR_EMAIL" \
  --role="roles/cloudsql.client"
```

### データベース接続エラー

**症状**: `FATAL: password authentication failed`

**解決方法**:

1. パスワードを確認

```bash
# Secret Managerから取得
gcloud secrets versions access latest --secret=database-password --project=YOUR_PROJECT_ID
```

2. ユーザーを再作成

```bash
gcloud sql users set-password polibase_user \
  --instance=INSTANCE_NAME \
  --password=NEW_PASSWORD \
  --project=YOUR_PROJECT_ID
```

### Cloud Runからの接続エラー

**症状**: Cloud Runサービスがデータベースに接続できない

**解決方法**:

1. Cloud SQL接続が設定されているか確認

```bash
gcloud run services describe polibase-ui \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID \
  --format='value(spec.template.spec.containers[0].cloudSqlInstances)'
```

2. 環境変数を確認

```bash
gcloud run services describe polibase-ui \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID \
  --format='value(spec.template.spec.containers[0].env)'
```

3. Cloud Runサービスアカウントに権限を付与

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/cloudsql.client"
```

### インポート/エクスポートエラー

**症状**: `AccessDeniedException` または timeout

**解決方法**:

1. Cloud SQL サービスアカウントにGCSアクセス権限を付与

```bash
# Cloud SQLサービスアカウントを確認
gcloud sql instances describe INSTANCE_NAME \
  --format='value(serviceAccountEmailAddress)' \
  --project=YOUR_PROJECT_ID

# GCSバケットへのアクセス権限を付与
gsutil iam ch serviceAccount:SERVICE_ACCOUNT_EMAIL:objectAdmin \
  gs://polibase-backups
```

2. ファイルサイズとタイムアウトを確認

```bash
# 大きなファイルの場合、圧縮を検討
gzip backup.sql
gsutil cp backup.sql.gz gs://polibase-backups/
```

---

## 参考リンク

- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Cloud SQL Auth Proxy](https://cloud.google.com/sql/docs/postgres/sql-proxy)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Terraform Google Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)

---

## 更新履歴

- 2024-01-XX: 初版作成（PBI-003対応）
