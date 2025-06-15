# データベース管理機能 動作確認ガイド

このドキュメントでは、データベースのバックアップ・リストア・マイグレーション機能の動作確認方法を説明します。

## 🔧 前提条件

- Docker Composeが起動していること
- PostgreSQL 15が動作していること
- （オプション）GCS認証が設定されていること

## 📋 主要機能

1. **バックアップ**: ローカルおよびGCSへのバックアップ
2. **リストア**: バックアップからのデータ復元
3. **マイグレーション**: スキーマの更新
4. **データベースリセット**: 初期状態へのリセット

## 🚀 クイックスタート

### 基本的な動作確認
```bash
# データベース管理テストスクリプトを実行
cd tests/integration/database
./test_database_management.sh

# または個別に実行
# 1. バックアップ（ローカル + GCS）
docker compose exec polibase uv run polibase database backup

# 2. バックアップ（ローカルのみ）
docker compose exec polibase uv run polibase database backup --no-gcs

# 3. バックアップ一覧
docker compose exec polibase uv run polibase database list

# 4. リストア（ローカルファイル）
docker compose exec polibase uv run polibase database restore backup_20240615_120000.sql

# 5. リストア（GCSから）
docker compose exec polibase uv run polibase database restore gs://your-bucket/backups/backup_20240615_120000.sql
```

## 📊 データ確認

### データベース状態の確認
```sql
-- テーブルとレコード数
SELECT
    schemaname,
    tablename,
    n_live_tup as row_count
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;

-- データベースサイズ
SELECT
    pg_database_size('polibase_db') as size_bytes,
    pg_size_pretty(pg_database_size('polibase_db')) as size_pretty;

-- 最新のマイグレーション確認
SELECT
    routine_name,
    created
FROM information_schema.routines
WHERE routine_schema = 'public'
ORDER BY created DESC
LIMIT 5;
```

## 🔍 トラブルシューティング

### よくある問題

1. **バックアップ失敗**
   ```bash
   # ディスク容量確認
   df -h /database/backups/

   # 権限確認
   ls -la database/backups/
   ```

2. **リストアエラー**
   ```bash
   # 接続中のセッションを切断
   docker compose exec postgres psql -U polibase_user -d postgres -c \
     "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'polibase_db';"
   ```

3. **マイグレーション順序**
   ```bash
   # マイグレーションファイル確認
   ls -1 database/migrations/*.sql | sort
   ```

## 📈 パフォーマンス指標

- バックアップ: 100MBで約10秒
- リストア: 100MBで約15秒
- GCSアップロード: ネットワーク速度に依存
- 圧縮率: 約70-80%削減

## 🧪 詳細テスト

```bash
# 詳細な動作確認（Python）
docker compose exec polibase uv run python tests/integration/database/test_database_detailed.py

# バックアップ・リストアの完全性テスト
docker compose exec polibase uv run python tests/integration/database/test_backup_integrity.py

# マイグレーションテスト
docker compose exec polibase uv run python tests/integration/database/test_migrations.py
```

## 📝 バックアップ戦略

### 自動バックアップ設定
```bash
# Cronジョブ例（毎日午前2時にバックアップ）
0 2 * * * docker compose exec -T polibase uv run polibase database backup

# 保持期間付きバックアップ（7日間保持）
find database/backups -name "backup_*.sql" -mtime +7 -delete
```

### バックアップファイル命名規則
```
# ローカル
database/backups/backup_YYYYMMDD_HHMMSS.sql

# GCS
gs://your-bucket/backups/backup_YYYYMMDD_HHMMSS.sql
```

## 🔄 データベースリセット

### 完全リセット（注意: すべてのデータが削除されます）
```bash
# リセットスクリプト実行
./reset-database.sh

# または手動で
docker compose down -v
docker compose up -d
docker compose exec polibase uv run python -c "from src.config.database import test_connection; test_connection()"
```

### 部分リセット
```sql
-- 特定のテーブルのみクリア
TRUNCATE TABLE conversations CASCADE;
TRUNCATE TABLE speakers CASCADE;

-- 外部キー制約を一時無効化
SET session_replication_role = 'replica';
TRUNCATE TABLE politicians CASCADE;
SET session_replication_role = 'origin';
```

## 🛡️ セキュリティ

### バックアップの暗号化
```bash
# 暗号化バックアップ
docker compose exec polibase uv run polibase database backup | \
  openssl enc -aes-256-cbc -salt -out backup.sql.enc

# 復号化
openssl enc -d -aes-256-cbc -in backup.sql.enc | \
  docker compose exec -T polibase uv run polibase database restore -
```

### アクセス制限
```sql
-- 読み取り専用ユーザーの作成
CREATE USER readonly_user WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE polibase_db TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
```
