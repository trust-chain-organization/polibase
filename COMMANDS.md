# Polibase コマンドリファレンス

このファイルは、Polibaseで使用可能なすべてのコマンドの詳細なリファレンスです。

## 目次

- [統一CLIコマンド](#統一cliコマンド)
- [従来の実行方法](#従来の実行方法)
- [データベース管理](#データベース管理)
- [開発用コマンド](#開発用コマンド)
- [トラブルシューティング用コマンド](#トラブルシューティング用コマンド)

## 統一CLIコマンド

新しく統一されたCLIインターフェースです。すべてのコマンドは `docker compose exec polibase uv run polibase` の後に続きます。

### 基本コマンド

```bash
# 利用可能なコマンドを表示
docker compose -f docker/docker-compose.yml exec polibase uv run polibase --help

# データベース接続をテスト
docker compose -f docker/docker-compose.yml exec polibase uv run polibase test-connection
```

### 議事録処理

```bash
# 議事録を処理（発言を抽出）
docker compose -f docker/docker-compose.yml exec polibase uv run polibase process-minutes

# GCSから議事録を取得して処理（meeting IDを指定）
docker compose -f docker/docker-compose.yml exec polibase uv run polibase process-minutes --meeting-id 123

# 議事録から発言者情報を抽出
docker compose -f docker/docker-compose.yml exec polibase uv run polibase extract-speakers

# 発言者をマッチング（LLM使用）
docker compose -f docker/docker-compose.yml exec polibase uv run polibase update-speakers --use-llm
```

### Web UI

```bash
# 会議管理Web UIを起動
docker compose -f docker/docker-compose.yml exec polibase uv run polibase streamlit

# カスタムホストで起動
docker compose -f docker/docker-compose.yml exec polibase uv run polibase streamlit --host 0.0.0.0

# カスタムポートで起動
docker compose -f docker/docker-compose.yml exec polibase uv run polibase streamlit --port 8080

# データカバレッジ監視ダッシュボードを起動
docker compose -f docker/docker-compose.yml exec polibase uv run polibase monitoring

# カスタムポートで監視ダッシュボードを起動
docker compose -f docker/docker-compose.yml exec polibase uv run polibase monitoring --port 8503
```

### Webスクレイピング

#### 議事録取得

```bash
# 単一の議事録を取得（kaigiroku.net対応）
docker compose -f docker/docker-compose.yml exec polibase uv run polibase scrape-minutes "https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=6030&schedule_id=1"

# 出力形式とディレクトリを指定
docker compose -f docker/docker-compose.yml exec polibase uv run polibase scrape-minutes "URL" --output-dir data/scraped --format txt

# キャッシュを無視して再取得
docker compose -f docker/docker-compose.yml exec polibase uv run polibase scrape-minutes "URL" --no-cache

# Google Cloud Storageにアップロード（meetingsテーブルにGCS URIを自動保存）
docker compose -f docker/docker-compose.yml exec polibase uv run polibase scrape-minutes "URL" --upload-to-gcs
docker compose -f docker/docker-compose.yml exec polibase uv run polibase scrape-minutes "URL" --upload-to-gcs --gcs-bucket my-bucket

# 複数の議事録を一括取得（kaigiroku.net）
docker compose -f docker/docker-compose.yml exec polibase uv run polibase batch-scrape --tenant kyoto --start-id 6000 --end-id 6100
docker compose -f docker/docker-compose.yml exec polibase uv run polibase batch-scrape --tenant osaka --start-id 1000 --end-id 1100

# バッチ取得でGCSにアップロード
docker compose -f docker/docker-compose.yml exec polibase uv run polibase batch-scrape --tenant kyoto --upload-to-gcs
```

#### 政党議員情報取得

```bash
# 全政党の議員情報を取得（議員一覧URLが設定されている政党）
docker compose -f docker/docker-compose.yml exec polibase uv run polibase scrape-politicians --all-parties

# 特定の政党のみ取得（政党IDを指定）
docker compose -f docker/docker-compose.yml exec polibase uv run polibase scrape-politicians --party-id 5

# ドライラン（データベースに保存せずに確認）
docker compose -f docker/docker-compose.yml exec polibase uv run polibase scrape-politicians --all-parties --dry-run

# 最大ページ数を指定（ページネーション対応）
docker compose -f docker/docker-compose.yml exec polibase uv run polibase scrape-politicians --all-parties --max-pages 5
```

### 会議体所属議員の抽出・マッチング

```bash
# ステップ1: 議員情報の抽出
docker compose -f docker/docker-compose.yml exec polibase uv run polibase extract-conference-members --conference-id 185
docker compose -f docker/docker-compose.yml exec polibase uv run polibase extract-conference-members --force  # 再抽出

# ステップ2: 既存政治家とのマッチング
docker compose -f docker/docker-compose.yml exec polibase uv run polibase match-conference-members --conference-id 185
docker compose -f docker/docker-compose.yml exec polibase uv run polibase match-conference-members  # 全保留データを処理

# ステップ3: 所属情報の作成
docker compose -f docker/docker-compose.yml exec polibase uv run polibase create-affiliations --conference-id 185
docker compose -f docker/docker-compose.yml exec polibase uv run polibase create-affiliations --start-date 2024-01-01

# 処理状況の確認
docker compose -f docker/docker-compose.yml exec polibase uv run polibase member-status --conference-id 185
```

### 監視ダッシュボード（専用コンテナ）

```bash
# 監視ダッシュボード（専用コンテナ）
docker compose -f docker/docker-compose.yml up -d polibase-monitoring
```

## データベース管理

### バックアップ・リストア（新しい方法）

```bash
# ローカルとGCSの両方にバックアップ（デフォルト）
docker compose -f docker/docker-compose.yml exec polibase uv run polibase database backup

# ローカルのみにバックアップ
docker compose -f docker/docker-compose.yml exec polibase uv run polibase database backup --no-gcs

# バックアップ一覧の確認
docker compose -f docker/docker-compose.yml exec polibase uv run polibase database list
docker compose -f docker/docker-compose.yml exec polibase uv run polibase database list --no-gcs

# リストア実行
docker compose -f docker/docker-compose.yml exec polibase uv run polibase database restore database/backups/polibase_backup_20241230_123456.sql
docker compose -f docker/docker-compose.yml exec polibase uv run polibase database restore gs://polibase-scraped-minutes/database-backups/polibase_backup_20241230_123456.sql
```

### 直接データベース操作

```bash
# PostgreSQLに接続
docker compose -f docker/docker-compose.yml exec postgres psql -U polibase_user -d polibase_db

# 手動バックアップ
docker compose -f docker/docker-compose.yml exec postgres pg_dump -U polibase_user polibase_db > backup.sql

# 手動リストア
docker compose -f docker/docker-compose.yml exec -T postgres psql -U polibase_user -d polibase_db < backup.sql

# マイグレーションの適用
docker compose -f docker/docker-compose.yml exec postgres psql -U polibase_user -d polibase_db -f /docker-entrypoint-initdb.d/migrations/004_add_gcs_uri_to_meetings.sql
```

## 開発用コマンド

### テスト

```bash
# 全テスト実行
docker compose -f docker/docker-compose.yml exec polibase uv run pytest

# 特定のテストを実行
docker compose -f docker/docker-compose.yml exec polibase uv run pytest tests/test_minutes_divider.py -v

# カバレッジレポート付き
docker compose -f docker/docker-compose.yml exec polibase uv run pytest --cov=src tests/
```

### コード品質

```bash
# 依存関係のインストール
docker compose -f docker/docker-compose.yml exec polibase uv sync

# コードフォーマット
docker compose -f docker/docker-compose.yml exec polibase uv run --frozen ruff format .

# リンティング
docker compose -f docker/docker-compose.yml exec polibase uv run --frozen ruff check .
docker compose -f docker/docker-compose.yml exec polibase uv run --frozen ruff check . --fix  # 自動修正

# 型チェック
docker compose -f docker/docker-compose.yml exec polibase uv run --frozen pyright

# pre-commitフック
docker compose -f docker/docker-compose.yml exec polibase uv run pre-commit install
docker compose -f docker/docker-compose.yml exec polibase uv run pre-commit run --all-files
```

## トラブルシューティング用コマンド

### データベース関連

```bash
# 接続テスト
docker compose -f docker/docker-compose.yml exec polibase uv run python -c "from src.config.database import test_connection; test_connection()"

# PostgreSQLログの確認
docker compose -f docker/docker-compose.yml logs postgres

# データベースの状態確認
docker compose -f docker/docker-compose.yml exec postgres psql -U polibase_user -d polibase_db -c "\dt"
```


## クイックリファレンス

よく使うコマンドの短縮版です。

```bash
# 🏗️ 初期セットアップ
cp .env.example .env
docker compose -f docker/docker-compose.yml up -d
./test-setup.sh

# 🔄 通常の起動・停止
docker compose -f docker/docker-compose.yml up -d      # バックグラウンド起動
docker compose -f docker/docker-compose.yml down       # 停止（データは保持）
docker compose -f docker/docker-compose.yml logs -f    # ログ確認

# 💾 データベース管理
./backup-database.sh backup           # バックアップ作成
./backup-database.sh list             # バックアップ一覧
./reset-database.sh                   # データベースリセット

# 🏃 主要な処理実行
docker compose -f docker/docker-compose.yml exec polibase uv run polibase process-minutes      # 議事録分割
docker compose -f docker/docker-compose.yml exec polibase uv run polibase extract-speakers      # 発言者抽出
docker compose -f docker/docker-compose.yml exec polibase uv run polibase update-speakers --use-llm  # LLM発言者マッチング
docker compose -f docker/docker-compose.yml exec polibase uv run polibase scrape-politicians --all-parties  # 政治家情報取得

# 🗃️ データベース操作
docker compose -f docker/docker-compose.yml exec postgres psql -U polibase_user -d polibase_db  # DB接続
```
