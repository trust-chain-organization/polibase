# BIダッシュボード 運用手順書

## 目次
1. [概要](#概要)
2. [前提条件](#前提条件)
3. [セットアップ手順](#セットアップ手順)
4. [起動・停止手順](#起動停止手順)
5. [環境変数の設定](#環境変数の設定)
6. [バックアップ・復旧手順](#バックアップ復旧手順)
7. [モニタリング方法](#モニタリング方法)
8. [ログの確認方法](#ログの確認方法)
9. [アップデート手順](#アップデート手順)
10. [運用チェックリスト](#運用チェックリスト)

---

## 概要

このドキュメントは、Polibase BIダッシュボードの運用担当者向けの手順書です。ダッシュボードのセットアップ、起動・停止、モニタリング、トラブルシューティングなどの運用作業を記載しています。

---

## 前提条件

### 必要なソフトウェア

- Docker 20.10.0以降
- Docker Compose 2.0.0以降
- PostgreSQL 15（Polibaseデータベース）
- Just（タスクランナー）

### 必要な権限

- Dockerコンテナの起動・停止権限
- ポート8050の使用権限
- データベースへの読み取り権限

### ネットワーク要件

- ポート8050: BIダッシュボード用
- ポート5432: PostgreSQL用
- ローカルネットワーク内からのアクセスが必要

---

## セットアップ手順

### 1. 初回セットアップ

#### 1.1. リポジトリのクローン

```bash
# リポジトリをクローン
git clone https://github.com/trust-chain-organization/polibase.git
cd polibase
```

#### 1.2. 環境変数の設定

```bash
# .envファイルを作成
cp .env.example .env

# .envファイルを編集
vi .env
```

必要な環境変数：
- `DATABASE_URL`: PostgreSQL接続URL
- `GOOGLE_API_KEY`: Google Gemini API Key（オプション）

#### 1.3. PostgreSQLの起動

```bash
# PostgreSQLを起動
just up
```

#### 1.4. データベースの初期化

```bash
# データベースマイグレーションを実行
just db-migrate
```

#### 1.5. BIダッシュボードのビルド

```bash
# BIダッシュボードをビルド
docker compose -f docker/docker-compose.yml build bi-dashboard
```

### 2. 動作確認

```bash
# BIダッシュボードを起動
just bi-dashboard-up

# ブラウザでアクセス
# http://localhost:8050

# ダッシュボードが表示されることを確認
# サマリーカード、グラフ、テーブルが表示されるか確認

# 停止
just bi-dashboard-down
```

---

## 起動・停止手順

### 起動手順

#### 方法1: フォアグラウンドで起動

```bash
# すべてのサービスを起動（PostgreSQL含む）
just up

# BIダッシュボードのみを起動
just bi-dashboard
```

このコマンドは、ターミナルにログを表示し続けます。終了するには `Ctrl + C` を押してください。

#### 方法2: バックグラウンドで起動

```bash
# すべてのサービスを起動（PostgreSQL含む）
docker compose -f docker/docker-compose.yml up -d

# BIダッシュボードのみを起動
just bi-dashboard-up
```

このコマンドは、バックグラウンドでサービスを起動します。

### 停止手順

#### 方法1: 特定のサービスを停止

```bash
# BIダッシュボードのみを停止
just bi-dashboard-down
```

#### 方法2: すべてのサービスを停止

```bash
# すべてのサービスを停止
docker compose -f docker/docker-compose.yml down
```

### 再起動手順

```bash
# BIダッシュボードを再起動
just bi-dashboard-down
just bi-dashboard-up
```

---

## 環境変数の設定

### 必須環境変数

| 変数名 | 説明 | デフォルト値 | 例 |
|--------|------|--------------|-----|
| `DATABASE_URL` | PostgreSQL接続URL | `postgresql://sagebase_user:sagebase_password@postgres:5432/sagebase_db` | `postgresql://user:pass@host:5432/db` |

### オプション環境変数

| 変数名 | 説明 | デフォルト値 | 例 |
|--------|------|--------------|-----|
| `GOOGLE_API_KEY` | Google Gemini API Key | なし | `AIzaSy...` |

### 環境変数の変更方法

#### 1. .envファイルを編集

```bash
vi .env
```

#### 2. docker-compose.ymlを編集

```bash
vi docker/docker-compose.yml
```

`bi-dashboard` サービスの `environment` セクションを編集：

```yaml
services:
  bi-dashboard:
    environment:
      - DATABASE_URL=postgresql://sagebase_user:sagebase_password@postgres:5432/sagebase_db
```

#### 3. サービスを再起動

```bash
just bi-dashboard-down
just bi-dashboard-up
```

---

## バックアップ・復旧手順

### データベースのバックアップ

BIダッシュボードはデータを保存しないため、データベースのバックアップが重要です。

#### 1. PostgreSQLのバックアップ

```bash
# データベース全体をバックアップ
docker compose -f docker/docker-compose.yml exec postgres pg_dump -U sagebase_user -d sagebase_db > backup_$(date +%Y%m%d).sql
```

#### 2. 定期バックアップの設定

```bash
# cronジョブを設定
crontab -e
```

以下を追加：

```
# 毎日午前2時にバックアップ
0 2 * * * cd /path/to/polibase && docker compose -f docker/docker-compose.yml exec postgres pg_dump -U sagebase_user -d sagebase_db > backup_$(date +\%Y\%m\%d).sql
```

### データベースの復旧

```bash
# データベースを復旧
docker compose -f docker/docker-compose.yml exec -T postgres psql -U sagebase_user -d sagebase_db < backup_20250101.sql
```

### BIダッシュボードの復旧

BIダッシュボードはステートレスなため、コンテナを再起動するだけで復旧できます。

```bash
# コンテナを再起動
just bi-dashboard-down
just bi-dashboard-up
```

---

## モニタリング方法

### 1. サービスの状態確認

```bash
# すべてのサービスの状態を確認
docker compose -f docker/docker-compose.yml ps

# BIダッシュボードの状態を確認
docker compose -f docker/docker-compose.yml ps bi-dashboard
```

出力例：

```
NAME                      IMAGE                   COMMAND                  SERVICE         STATUS
polibase-bi-dashboard     polibase-bi-dashboard   "python app.py"          bi-dashboard    Up 2 hours
```

### 2. リソース使用状況の確認

```bash
# CPU、メモリ使用率を確認
docker stats sagebase-bi-dashboard
```

出力例：

```
CONTAINER ID   NAME                    CPU %     MEM USAGE / LIMIT     MEM %     NET I/O           BLOCK I/O
abc123...      polibase-bi-dashboard   0.50%     150MiB / 2GiB         7.50%     1.2kB / 850B      0B / 0B
```

### 3. 接続テスト

```bash
# ダッシュボードにアクセス可能か確認
curl http://localhost:8050

# ステータスコード200が返れば正常
```

### 4. データベース接続確認

```bash
# データベースに接続できるか確認
docker compose -f docker/docker-compose.yml exec bi-dashboard python -c "
from data.data_loader import get_database_url
from sqlalchemy import create_engine
engine = create_engine(get_database_url())
with engine.connect() as conn:
    result = conn.execute('SELECT 1')
    print('Database connection: OK')
"
```

### 5. 定期モニタリングスクリプト

以下のスクリプトを作成して、定期的に実行することを推奨します。

```bash
#!/bin/bash
# monitoring.sh

echo "=== BIダッシュボード モニタリング ==="
echo "日時: $(date)"
echo ""

# サービスの状態確認
echo "1. サービスの状態:"
docker compose -f docker/docker-compose.yml ps bi-dashboard
echo ""

# リソース使用状況
echo "2. リソース使用状況:"
docker stats sagebase-bi-dashboard --no-stream
echo ""

# 接続テスト
echo "3. 接続テスト:"
if curl -s http://localhost:8050 > /dev/null; then
    echo "✓ ダッシュボードにアクセス可能"
else
    echo "✗ ダッシュボードにアクセスできません"
fi
echo ""

echo "=== モニタリング完了 ==="
```

---

## ログの確認方法

### 1. リアルタイムログの確認

```bash
# BIダッシュボードのログをリアルタイムで表示
docker compose -f docker/docker-compose.yml logs -f bi-dashboard
```

終了するには `Ctrl + C` を押してください。

### 2. 過去のログの確認

```bash
# 過去100行のログを表示
docker compose -f docker/docker-compose.yml logs --tail=100 bi-dashboard

# 特定の時刻以降のログを表示
docker compose -f docker/docker-compose.yml logs --since="2025-01-01T00:00:00" bi-dashboard
```

### 3. エラーログのフィルタリング

```bash
# エラーのみを表示
docker compose -f docker/docker-compose.yml logs bi-dashboard | grep -i error

# 警告のみを表示
docker compose -f docker/docker-compose.yml logs bi-dashboard | grep -i warning
```

### 4. ログのエクスポート

```bash
# ログをファイルに保存
docker compose -f docker/docker-compose.yml logs bi-dashboard > bi-dashboard-logs-$(date +%Y%m%d).log
```

---

## アップデート手順

### 1. コードのアップデート

```bash
# 最新のコードを取得
git pull origin main

# BIダッシュボードを停止
just bi-dashboard-down

# イメージを再ビルド
docker compose -f docker/docker-compose.yml build bi-dashboard

# BIダッシュボードを起動
just bi-dashboard-up

# 動作確認
curl http://localhost:8050
```

### 2. 依存関係のアップデート

```bash
# requirements.txtを更新
vi src/interfaces/bi_dashboard/requirements.txt

# イメージを再ビルド
docker compose -f docker/docker-compose.yml build bi-dashboard --no-cache

# BIダッシュボードを起動
just bi-dashboard-up
```

### 3. データベースマイグレーション

```bash
# マイグレーションファイルを確認
ls -la database/migrations/

# マイグレーションを実行
just db-migrate

# BIダッシュボードを再起動
just bi-dashboard-down
just bi-dashboard-up
```

### 4. ロールバック

アップデート後に問題が発生した場合のロールバック手順：

```bash
# 前のバージョンに戻る
git checkout <previous-commit-hash>

# イメージを再ビルド
docker compose -f docker/docker-compose.yml build bi-dashboard

# BIダッシュボードを起動
just bi-dashboard-up
```

---

## 運用チェックリスト

### 日次チェック

- [ ] ダッシュボードにアクセス可能か
- [ ] サービスが正常に動作しているか
- [ ] エラーログに異常がないか
- [ ] リソース使用率が正常範囲内か（CPU < 80%, メモリ < 80%）

### 週次チェック

- [ ] データベースのバックアップが取れているか
- [ ] ログファイルのサイズが肥大化していないか
- [ ] データの整合性が保たれているか
- [ ] パフォーマンスが低下していないか

### 月次チェック

- [ ] 依存関係の更新が必要か
- [ ] セキュリティアップデートが必要か
- [ ] ディスク容量が十分か
- [ ] 長期的なパフォーマンストレンドを確認

### トラブル発生時

- [ ] エラーログを確認
- [ ] [トラブルシューティングガイド](./BI_DASHBOARD_TROUBLESHOOTING.md)を参照
- [ ] 必要に応じて開発チームにエスカレーション

---

## 緊急連絡先

### 運用チーム

- メール: operations@example.com
- Slack: #polibase-operations

### 開発チーム

- メール: dev@example.com
- Slack: #polibase-dev
- GitHub Issues: https://github.com/trust-chain-organization/polibase/issues

---

## 関連ドキュメント

- [BIダッシュボード概要](../BI_DASHBOARD.md)
- [ユーザーガイド](./BI_DASHBOARD_USER_GUIDE.md)
- [トラブルシューティングガイド](./BI_DASHBOARD_TROUBLESHOOTING.md)
