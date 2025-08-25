# トラブルシューティングガイド

## 目次
- [よくある問題と解決方法](#よくある問題と解決方法)
- [エラーコード一覧](#エラーコード一覧)
- [パフォーマンスチューニング](#パフォーマンスチューニング)
- [ログ分析方法](#ログ分析方法)
- [緊急対応手順](#緊急対応手順)

## よくある問題と解決方法

### 環境構築の問題

#### Docker起動エラー

**症状:** `docker compose up`実行時にエラーが発生

**原因と解決方法:**

```bash
# 1. Dockerデーモンが起動しているか確認
docker ps

# 2. ポート競合の確認
lsof -i :8501
lsof -i :5432

# 3. 既存コンテナの停止とクリーンアップ
docker compose down
docker system prune -f

# 4. 再起動
docker compose -f docker/docker-compose.yml up -d
```

#### git worktreeでのポート競合

**症状:** 複数のworktreeで同時実行時にポートエラー

**解決方法:**
```bash
# docker-compose.override.ymlが自動生成されているか確認
ls docker/docker-compose.override.yml

# 両方のファイルを指定して起動
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml up -d

# 実際のポート番号を確認
docker ps
```

### データベース関連

#### 接続エラー

**症状:** `psycopg2.OperationalError: could not connect to server`

**解決方法:**
```bash
# 1. 環境変数の確認
echo $DATABASE_URL

# 2. PostgreSQLコンテナの状態確認
docker compose ps postgres
docker compose logs postgres

# 3. 接続テスト
docker compose exec polibase python -c "
from src.config.database import test_connection
test_connection()
"

# 4. データベースの再初期化
./reset-database.sh
```

#### マイグレーションエラー

**症状:** テーブルが見つからない、カラムが存在しない

**解決方法:**
```bash
# 1. 現在のスキーマ確認
docker compose exec postgres psql -U polibase_user -d polibase_db -c "\dt"

# 2. マイグレーション実行
docker compose exec polibase cat database/migrations/*.sql | \
  docker compose exec -T postgres psql -U polibase_user -d polibase_db

# 3. 特定のマイグレーションのみ実行
docker compose exec polibase cat database/migrations/017_add_process_id_to_minutes.sql | \
  docker compose exec -T postgres psql -U polibase_user -d polibase_db
```

### LLM処理関連

#### API キーエラー

**症状:** `google.generativeai.types.generation_types.BlockedPromptException`

**解決方法:**
```bash
# 1. APIキーの確認
echo $GOOGLE_API_KEY

# 2. .envファイルの確認
grep GOOGLE_API_KEY .env

# 3. 環境変数の再読み込み
docker compose down
docker compose up -d

# 4. APIキーの検証
docker compose exec polibase python -c "
import os
import google.generativeai as genai
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')
print('API key is valid')
"
```

#### レート制限エラー

**症状:** `429 Resource has been exhausted`

**解決方法:**
```python
# src/infrastructure/external/gemini_llm_service.py に追加
import time
from tenacity import retry, stop_after_attempt, wait_exponential

class GeminiLLMService:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def extract_conversations(self, text: str):
        try:
            response = await self.model.generate_content_async(prompt)
            return self._parse_response(response.text)
        except Exception as e:
            if "429" in str(e):
                time.sleep(60)  # 1分待機
                raise
            raise
```

### スクレイピング関連

#### Playwright エラー

**症状:** `playwright._impl._api_types.Error: Browser closed`

**解決方法:**
```bash
# 1. Chromiumの確認
docker compose exec polibase which chromium

# 2. 依存パッケージのインストール
docker compose exec polibase apt-get update && apt-get install -y \
  libglib2.0-0 libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
  libcups2 libdrm2 libdbus-1-3 libxkbcommon0 libx11-6 \
  libxcomposite1 libxdamage1 libxext6 libxfixes3 libxrandr2 \
  libgbm1 libxcb1 libxss1 libasound2

# 3. Playwrightの再インストール
docker compose exec polibase uv pip install --force-reinstall playwright
docker compose exec polibase playwright install chromium
```

### パフォーマンス問題

#### 処理速度が遅い

**症状:** 議事録処理やスクレイピングが異常に遅い

**診断と解決:**
```bash
# 1. リソース使用状況確認
docker stats

# 2. データベースのスロークエリ確認
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"

# 3. インデックスの確認と追加
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
CREATE INDEX CONCURRENTLY idx_conversations_speaker_id
ON conversations(speaker_id);
"

# 4. バキューム実行
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
VACUUM ANALYZE;
"
```

## エラーコード一覧

### アプリケーションエラー

| コード | エラー名 | 説明 | 対処法 |
|--------|---------|------|--------|
| `E001` | `MeetingNotFoundException` | 会議が見つからない | 会議IDを確認 |
| `E002` | `ProcessingException` | 処理中にエラー | ログを確認 |
| `E003` | `DuplicatePoliticianException` | 政治家が重複 | 既存データを確認 |
| `E004` | `InvalidDataException` | データが不正 | 入力データを検証 |
| `E005` | `LLMServiceException` | LLMサービスエラー | APIキーとレート制限を確認 |

### HTTPエラー

| コード | 説明 | 対処法 |
|--------|------|--------|
| `400` | 不正なリクエスト | パラメータを確認 |
| `401` | 認証エラー | APIキーを確認 |
| `403` | アクセス拒否 | 権限を確認 |
| `404` | リソースが見つからない | URLとIDを確認 |
| `429` | レート制限超過 | 待機後に再試行 |
| `500` | サーバーエラー | ログを確認 |
| `503` | サービス利用不可 | しばらく待機 |

## パフォーマンスチューニング

### データベース最適化

#### インデックス追加
```sql
-- 頻繁に検索されるカラムにインデックス追加
CREATE INDEX idx_politicians_name ON politicians(name);
CREATE INDEX idx_speakers_name ON speakers(name);
CREATE INDEX idx_meetings_date ON meetings(date);
CREATE INDEX idx_conversations_sequence ON conversations(minutes_id, sequence_number);
```

#### クエリ最適化
```python
# Bad: N+1問題
meetings = session.query(Meeting).all()
for meeting in meetings:
    print(meeting.conversations)  # 各meetingごとにクエリ

# Good: Eager Loading
from sqlalchemy.orm import selectinload
meetings = session.query(Meeting)\
    .options(selectinload(Meeting.conversations))\
    .all()
```

### メモリ使用量削減

```python
# Bad: 全データをメモリに載せる
all_conversations = session.query(Conversation).all()
for conv in all_conversations:
    process(conv)

# Good: チャンク処理
def process_in_chunks(query, chunk_size=1000):
    offset = 0
    while True:
        chunk = query.limit(chunk_size).offset(offset).all()
        if not chunk:
            break
        for item in chunk:
            yield item
        offset += chunk_size

for conv in process_in_chunks(session.query(Conversation)):
    process(conv)
```

### 並列処理の活用

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def process_parallel(items):
    """並列処理で高速化"""
    with ThreadPoolExecutor(max_workers=5) as executor:
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(executor, process_item, item)
            for item in items
        ]
        return await asyncio.gather(*tasks)
```

## ログ分析方法

### ログファイルの場所

```bash
# Dockerコンテナ内
/app/logs/app.log
/var/log/polibase/

# ホストマシン
./logs/
docker compose logs polibase
```

### ログレベル設定

```python
# .env
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# src/utils/logger.py
import logging
import os

logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### ログ検索とフィルタリング

```bash
# エラーログのみ表示
docker compose logs polibase | grep ERROR

# 特定の日時範囲
docker compose logs --since "2024-08-01" --until "2024-08-02" polibase

# リアルタイム監視
docker compose logs -f polibase

# 特定のモジュールのログ
docker compose logs polibase | grep "minutes_divider"
```

### 構造化ログの解析

```python
import json
from datetime import datetime

def analyze_logs(log_file):
    """JSONログの解析"""
    errors = []
    warnings = []

    with open(log_file, 'r') as f:
        for line in f:
            try:
                log = json.loads(line)
                if log['level'] == 'ERROR':
                    errors.append(log)
                elif log['level'] == 'WARNING':
                    warnings.append(log)
            except json.JSONDecodeError:
                continue

    return {
        'error_count': len(errors),
        'warning_count': len(warnings),
        'errors': errors[-10:],  # 最新10件
        'warnings': warnings[-10:]
    }
```

## 緊急対応手順

### システム停止時

```bash
# 1. 状態確認
docker compose ps
systemctl status docker

# 2. ログ確認
docker compose logs --tail=100 polibase
journalctl -u docker -n 100

# 3. 緊急再起動
docker compose down
docker system prune -f
docker compose up -d

# 4. ヘルスチェック
curl http://localhost:8501/health
```

### データ破損時

```bash
# 1. 即座にサービス停止
docker compose stop polibase

# 2. バックアップから復元
docker compose exec polibase uv run polibase database list
docker compose exec polibase uv run polibase database restore backup_20240801.sql

# 3. データ整合性チェック
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT COUNT(*) FROM politicians;
SELECT COUNT(*) FROM meetings;
SELECT COUNT(*) FROM conversations;
"

# 4. サービス再開
docker compose start polibase
```

### セキュリティインシデント

```bash
# 1. 影響範囲の特定
grep "suspicious" /var/log/polibase/*.log

# 2. APIキーの無効化と再発行
# Google Cloud Consoleでキーを無効化

# 3. 環境変数の更新
vi .env  # 新しいAPIキーに更新

# 4. コンテナ再起動
docker compose down
docker compose up -d

# 5. 監査ログの確認
docker compose exec postgres psql -U polibase_user -d polibase_db -c "
SELECT * FROM audit_log
WHERE created_at >= NOW() - INTERVAL '1 day'
ORDER BY created_at DESC;
"
```

## サポート連絡先

### 問題報告

GitHub Issues: https://github.com/trust-chain-organization/polibase/issues

**報告時に含める情報:**
- エラーメッセージ全文
- 実行したコマンド
- 環境情報（OS、Dockerバージョン）
- ログファイル（該当部分）

### ドキュメント

- [アーキテクチャ概要](../architecture/README.md)
- [開発ガイド](../guides/development.md)
- [ユーザーガイド](../user-guide/README.md)
- [API仕様](../api/README.md)
