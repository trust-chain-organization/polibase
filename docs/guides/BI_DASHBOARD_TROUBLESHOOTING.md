# BIダッシュボード トラブルシューティングガイド

## 目次
1. [概要](#概要)
2. [よくある問題と解決方法](#よくある問題と解決方法)
3. [エラーメッセージ別の対処方法](#エラーメッセージ別の対処方法)
4. [ログの確認方法](#ログの確認方法)
5. [デバッグ手順](#デバッグ手順)
6. [パフォーマンス問題](#パフォーマンス問題)
7. [エスカレーション基準](#エスカレーション基準)

---

## 概要

このドキュメントは、Polibase BIダッシュボードで発生する可能性のある問題と、その解決方法を記載したトラブルシューティングガイドです。

---

## よくある問題と解決方法

### 問題1: ダッシュボードにアクセスできない

#### 症状
- ブラウザで `http://localhost:8050` にアクセスすると、「接続できません」というエラーが表示される

#### 原因
1. BIダッシュボードが起動していない
2. ポート8050が他のプロセスで使用されている
3. ネットワーク接続に問題がある

#### 解決方法

**1. BIダッシュボードの起動確認**

```bash
# サービスの状態を確認
docker compose -f docker/docker-compose.yml ps bi-dashboard
```

出力が「Up」でない場合は、サービスを起動してください：

```bash
# BIダッシュボードを起動
just bi-dashboard-up
```

**2. ポート競合の確認**

```bash
# ポート8050を使用しているプロセスを確認
lsof -i :8050
```

他のプロセスがポート8050を使用している場合は、そのプロセスを停止するか、docker-compose.ymlでポート番号を変更してください。

**3. ネットワーク接続の確認**

```bash
# ローカルホストへの接続を確認
curl http://localhost:8050
```

---

### 問題2: データが表示されない

#### 症状
- ダッシュボードは起動するが、グラフやテーブルにデータが表示されない
- サマリーカードが「0」を表示している

#### 原因
1. データベースにデータが存在しない
2. データベース接続に問題がある
3. データ取得クエリにエラーがある

#### 解決方法

**1. データベースのデータ確認**

```bash
# データベースに接続
docker compose -f docker/docker-compose.yml exec postgres psql -U sagebase_user -d sagebase_db

# 自治体データを確認
SELECT COUNT(*) FROM governing_bodies;

# データがある場合は、100以上の数字が表示されるはず
# データがない場合は、データをインポートする必要があります
```

**2. データベース接続の確認**

```bash
# BIダッシュボードのログを確認
docker compose -f docker/docker-compose.yml logs bi-dashboard | grep -i "database\|connection\|error"
```

接続エラーがある場合は、環境変数 `DATABASE_URL` を確認してください。

**3. データの再取得**

ダッシュボードの「データを更新」ボタンをクリックして、データを再取得してください。

---

### 問題3: グラフが正しく表示されない

#### 症状
- グラフが空白で表示される
- グラフが壊れて表示される
- グラフのレイアウトが崩れている

#### 原因
1. ブラウザのキャッシュが古い
2. JavaScriptのエラーが発生している
3. データ形式に問題がある

#### 解決方法

**1. ブラウザのキャッシュをクリア**

- Windows: `Ctrl + Shift + Delete`
- Mac: `Cmd + Shift + Delete`

**2. JavaScriptエラーの確認**

ブラウザの開発者ツール（F12）を開き、コンソールタブでエラーを確認してください。

**3. 別のブラウザで試す**

Chrome、Firefox、Edgeなど、別のブラウザでアクセスして、問題が再現するか確認してください。

**4. データ形式の確認**

```bash
# BIダッシュボードのログを確認
docker compose -f docker/docker-compose.yml logs bi-dashboard | tail -50
```

---

### 問題4: 更新ボタンが機能しない

#### 症状
- 「データを更新」ボタンをクリックしても、データが更新されない
- ボタンをクリックしてもエラーが表示される

#### 原因
1. データベース接続に問題がある
2. データ取得クエリにエラーがある
3. JavaScriptのエラーが発生している

#### 解決方法

**1. ブラウザの開発者ツールで確認**

ブラウザの開発者ツール（F12）を開き、ネットワークタブで更新ボタンをクリックしたときのリクエストを確認してください。

**2. ログの確認**

```bash
# BIダッシュボードのログを確認
docker compose -f docker/docker-compose.yml logs -f bi-dashboard
```

更新ボタンをクリックして、ログにエラーが表示されるか確認してください。

**3. サービスの再起動**

```bash
# BIダッシュボードを再起動
just bi-dashboard-down
just bi-dashboard-up
```

---

### 問題5: パフォーマンスが遅い

#### 症状
- ダッシュボードの表示に時間がかかる
- グラフの読み込みが遅い
- 更新ボタンの応答が遅い

#### 原因
1. データベースのパフォーマンスが低下している
2. ネットワーク接続が遅い
3. リソースが不足している

#### 解決方法

詳細は [パフォーマンス問題](#パフォーマンス問題) セクションを参照してください。

---

## エラーメッセージ別の対処方法

### エラー1: `sqlalchemy.exc.OperationalError: could not connect to server`

#### 症状
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect to server: Connection refused
```

#### 原因
PostgreSQLサービスが起動していない、または接続情報が間違っている

#### 解決方法

**1. PostgreSQLの起動確認**

```bash
# PostgreSQLの状態を確認
docker compose -f docker/docker-compose.yml ps postgres
```

起動していない場合は、起動してください：

```bash
# PostgreSQLを起動
docker compose -f docker/docker-compose.yml up -d postgres
```

**2. 接続情報の確認**

```bash
# 環境変数を確認
docker compose -f docker/docker-compose.yml exec bi-dashboard env | grep DATABASE_URL
```

正しい接続情報であることを確認してください：
```
DATABASE_URL=postgresql://sagebase_user:sagebase_password@postgres:5432/sagebase_db
```

---

### エラー2: `Error starting userland proxy: listen tcp4 0.0.0.0:8050: bind: address already in use`

#### 症状
```
Error starting userland proxy: listen tcp4 0.0.0.0:8050: bind: address already in use
```

#### 原因
ポート8050が他のプロセスで使用されている

#### 解決方法

**1. ポートを使用しているプロセスを確認**

```bash
# ポート8050を使用しているプロセスを確認
lsof -i :8050
```

**2. プロセスを停止**

```bash
# プロセスIDを確認してkill
kill -9 <PID>
```

**3. または、ポート番号を変更**

`docker/docker-compose.yml` を編集：

```yaml
services:
  bi-dashboard:
    ports:
      - "8051:8050"  # 8050を8051に変更
```

---

### エラー3: `ModuleNotFoundError: No module named 'plotly'`

#### 症状
```
ModuleNotFoundError: No module named 'plotly'
```

#### 原因
依存関係がインストールされていない

#### 解決方法

**1. イメージを再ビルド**

```bash
# BIダッシュボードを停止
just bi-dashboard-down

# イメージを再ビルド（キャッシュなし）
docker compose -f docker/docker-compose.yml build bi-dashboard --no-cache

# BIダッシュボードを起動
just bi-dashboard-up
```

---

### エラー4: `KeyError: 'DATABASE_URL'`

#### 症状
```
KeyError: 'DATABASE_URL'
```

#### 原因
環境変数 `DATABASE_URL` が設定されていない

#### 解決方法

**1. docker-compose.ymlを確認**

`docker/docker-compose.yml` の `bi-dashboard` サービスの `environment` セクションを確認：

```yaml
services:
  bi-dashboard:
    environment:
      - DATABASE_URL=postgresql://sagebase_user:sagebase_password@postgres:5432/sagebase_db
```

**2. サービスを再起動**

```bash
just bi-dashboard-down
just bi-dashboard-up
```

---

## ログの確認方法

### リアルタイムログの確認

```bash
# BIダッシュボードのログをリアルタイムで表示
docker compose -f docker/docker-compose.yml logs -f bi-dashboard
```

### 過去のログの確認

```bash
# 過去100行のログを表示
docker compose -f docker/docker-compose.yml logs --tail=100 bi-dashboard
```

### エラーログのフィルタリング

```bash
# エラーのみを表示
docker compose -f docker/docker-compose.yml logs bi-dashboard | grep -i error

# 警告のみを表示
docker compose -f docker/docker-compose.yml logs bi-dashboard | grep -i warning
```

### 特定の時刻のログを確認

```bash
# 特定の時刻以降のログを表示
docker compose -f docker/docker-compose.yml logs --since="2025-01-01T00:00:00" bi-dashboard
```

---

## デバッグ手順

### 手順1: サービスの状態確認

```bash
# すべてのサービスの状態を確認
docker compose -f docker/docker-compose.yml ps

# BIダッシュボードの状態を確認
docker compose -f docker/docker-compose.yml ps bi-dashboard
```

### 手順2: ログの確認

```bash
# BIダッシュボードのログを確認
docker compose -f docker/docker-compose.yml logs --tail=50 bi-dashboard
```

### 手順3: コンテナ内でのデバッグ

```bash
# コンテナに入る
docker compose -f docker/docker-compose.yml exec bi-dashboard /bin/bash

# Pythonで直接テスト
python -c "
from data.data_loader import get_coverage_stats
stats = get_coverage_stats()
print(stats)
"
```

### 手順4: データベース接続の確認

```bash
# データベースに接続
docker compose -f docker/docker-compose.yml exec postgres psql -U sagebase_user -d sagebase_db

# データを確認
SELECT COUNT(*) FROM governing_bodies;
SELECT COUNT(*) FROM meetings;
```

### 手順5: ネットワークの確認

```bash
# BIダッシュボードからPostgreSQLへの接続を確認
docker compose -f docker/docker-compose.yml exec bi-dashboard ping postgres

# ポートの確認
docker compose -f docker/docker-compose.yml exec bi-dashboard nc -zv postgres 5432
```

---

## パフォーマンス問題

### 問題: グラフの表示が遅い（3秒以上）

#### 診断

**1. データベースクエリのパフォーマンスを確認**

```bash
# データベースに接続
docker compose -f docker/docker-compose.yml exec postgres psql -U sagebase_user -d sagebase_db

# クエリのパフォーマンスを確認
EXPLAIN ANALYZE
SELECT
    gb.id,
    gb.name,
    gb.organization_type,
    CASE
        WHEN gb.name ~ '^(北海道|.*[都道府県])' THEN
            SUBSTRING(gb.name FROM '^(北海道|.*?[都道府県])')
        ELSE
            '不明'
    END as prefecture,
    CASE
        WHEN COUNT(m.id) > 0 THEN true
        ELSE false
    END as has_data
FROM governing_bodies gb
LEFT JOIN conferences c ON gb.id = c.governing_body_id
LEFT JOIN meetings m ON c.id = m.conference_id
GROUP BY gb.id, gb.name, gb.organization_type
ORDER BY gb.organization_type, prefecture, gb.name;
```

**2. インデックスの確認**

```bash
# インデックスを確認
\d+ governing_bodies
\d+ conferences
\d+ meetings
```

#### 解決方法

**1. インデックスの追加**

```sql
-- governing_bodies.organization_typeにインデックスを追加
CREATE INDEX IF NOT EXISTS idx_governing_bodies_organization_type ON governing_bodies(organization_type);

-- conferences.governing_body_idにインデックスを追加
CREATE INDEX IF NOT EXISTS idx_conferences_governing_body_id ON conferences(governing_body_id);

-- meetings.conference_idにインデックスを追加
CREATE INDEX IF NOT EXISTS idx_meetings_conference_id ON meetings(conference_id);
```

**2. データベースの最適化**

```bash
# データベースに接続
docker compose -f docker/docker-compose.yml exec postgres psql -U sagebase_user -d sagebase_db

# VACUUM ANALYZE を実行
VACUUM ANALYZE governing_bodies;
VACUUM ANALYZE conferences;
VACUUM ANALYZE meetings;
```

---

### 問題: データ更新が遅い（5秒以上）

#### 診断

```bash
# リソース使用状況を確認
docker stats polibase-bi-dashboard --no-stream
docker stats postgres --no-stream
```

#### 解決方法

**1. リソースの増強**

`docker/docker-compose.yml` でメモリ制限を増やす：

```yaml
services:
  bi-dashboard:
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

**2. 接続プールの最適化**

`src/interfaces/bi_dashboard/data/data_loader.py` でSQLAlchemyの接続プールを最適化：

```python
def get_database_url() -> str:
    return os.getenv(
        "DATABASE_URL", "postgresql://polibase:polibase@localhost:5432/polibase"
    ) + "?pool_size=10&max_overflow=20"
```

---

### 問題: 同時アクセスでパフォーマンスが低下

#### 診断

```bash
# 同時接続数を確認
docker compose -f docker/docker-compose.yml exec postgres psql -U sagebase_user -d sagebase_db -c "SELECT count(*) FROM pg_stat_activity;"
```

#### 解決方法

**1. PostgreSQLの接続数を増やす**

```bash
# PostgreSQLの設定を確認
docker compose -f docker/docker-compose.yml exec postgres psql -U sagebase_user -d sagebase_db -c "SHOW max_connections;"

# 必要に応じて、PostgreSQLの設定を変更
```

**2. Gunicornの導入**

本番環境では、DashアプリをGunicornで実行することを推奨します。

---

## エスカレーション基準

以下の場合は、開発チームにエスカレーションしてください：

### レベル1: 緊急（即座にエスカレーション）

- [ ] ダッシュボードが完全に停止している
- [ ] データベースに接続できない
- [ ] セキュリティ上の問題が発生している
- [ ] データの整合性に問題がある

### レベル2: 高優先度（4時間以内にエスカレーション）

- [ ] パフォーマンスが著しく低下している（10秒以上）
- [ ] 一部の機能が動作しない
- [ ] エラーログに多数のエラーが記録されている
- [ ] リソース使用率が90%を超えている

### レベル3: 中優先度（1営業日以内にエスカレーション）

- [ ] 軽微なパフォーマンスの低下
- [ ] UIの表示に問題がある
- [ ] ドキュメントに記載されていない問題
- [ ] 改善提案

### エスカレーション時の情報

エスカレーション時には、以下の情報を提供してください：

1. **問題の詳細**
   - 発生時刻
   - 症状
   - 再現手順

2. **ログ**
   - BIダッシュボードのログ
   - データベースのログ
   - エラーメッセージ

3. **環境情報**
   - Dockerバージョン
   - OSバージョン
   - ブラウザバージョン

4. **試した対処方法**
   - このガイドで試した手順
   - 結果

---

## 関連ドキュメント

- [BIダッシュボード概要](../BI_DASHBOARD.md)
- [ユーザーガイド](./BI_DASHBOARD_USER_GUIDE.md)
- [運用手順書](./BI_DASHBOARD_OPERATIONS.md)
