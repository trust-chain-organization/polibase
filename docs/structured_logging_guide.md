# 構造化ログ運用ガイド

## 概要

Polibaseプロジェクトでは、システムの可観測性向上のため、structlogを使用した構造化ログを導入しています。
このドキュメントでは、構造化ログの使用方法と運用方針について説明します。

## 基本的な使い方

### ロガーの取得

```python
from src.common.logging import get_logger

logger = get_logger(__name__)
```

### ログの出力

構造化ログでは、メッセージに加えて構造化されたデータをキー・バリューペアで渡します：

```python
# 基本的なログ出力
logger.info("ユーザーがログインしました", user_id=123, ip_address="192.168.1.1")

# エラーログ
logger.error(
    "データベース接続エラー",
    error=str(e),
    database="postgres",
    retry_count=3,
    exc_info=True  # スタックトレースを含める
)

# パフォーマンスログ
logger.info(
    "処理完了",
    elapsed_ms=processing_time,
    records_processed=1000,
    throughput_per_sec=1000/processing_time
)
```

### コンテキスト管理

#### グローバルコンテキスト

リクエスト全体で共通の情報を設定できます：

```python
from src.common.logging import add_context, clear_context

# コンテキストを追加
add_context(request_id="req-123", user_id=456)

# 以降のログにはこれらの情報が自動的に含まれる
logger.info("処理開始")  # request_id, user_idが自動付与

# 処理終了後はクリア
clear_context()
```

#### ローカルコンテキスト

特定のスコープ内でのみ有効なコンテキスト：

```python
from src.common.logging import LogContext

with LogContext(operation="データインポート", file_name="data.csv"):
    logger.info("インポート開始")
    # 処理...
    logger.info("インポート完了", rows_imported=1000)
```

## ログフォーマット

### JSON形式（本番環境）

```json
{
  "event": "ユーザーがログインしました",
  "user_id": 123,
  "ip_address": "192.168.1.1",
  "level": "info",
  "logger": "src.auth.login",
  "timestamp": "2025-07-10T12:00:00.000Z",
  "filename": "login.py",
  "lineno": 42,
  "func_name": "handle_login"
}
```

### コンソール形式（開発環境）

```
2025-07-10T12:00:00.000Z [info     ] ユーザーがログインしました    [src.auth.login] user_id=123 ip_address=192.168.1.1
```

## 環境設定

### アプリケーション起動時の設定

```python
from src.common.logging import setup_logging

# 本番環境
setup_logging(log_level="INFO", json_format=True)

# 開発環境
setup_logging(log_level="DEBUG", json_format=False)

# テスト環境
setup_logging(log_level="WARNING", json_format=True, add_timestamp=False)
```

### 環境変数での制御

```bash
# ログレベル
export LOG_LEVEL=DEBUG

# ログフォーマット
export LOG_FORMAT=json  # または console
```

## ベストプラクティス

### 1. 構造化データを活用する

❌ 悪い例：
```python
logger.info(f"ユーザー{user_id}がログインしました")
```

✅ 良い例：
```python
logger.info("ユーザーがログインしました", user_id=user_id)
```

### 2. 適切なログレベルを使用する

- **DEBUG**: 詳細なデバッグ情報
- **INFO**: 通常の処理フロー
- **WARNING**: 注意が必要だが処理は継続
- **ERROR**: エラーだが復旧可能
- **CRITICAL**: システム全体に影響する致命的エラー

### 3. エラーログには詳細情報を含める

```python
try:
    result = process_data(data)
except ProcessingError as e:
    logger.error(
        "データ処理エラー",
        error=str(e),
        data_size=len(data),
        processing_stage="validation",
        exc_info=True  # スタックトレースを含める
    )
```

### 4. パフォーマンス計測を組み込む

```python
import time

start_time = time.time()
result = heavy_processing()
elapsed_ms = (time.time() - start_time) * 1000

logger.info(
    "重い処理が完了",
    elapsed_ms=elapsed_ms,
    result_size=len(result)
)
```

## ログの検索と分析

### jqを使用した検索

```bash
# エラーログのみ表示
docker compose exec polibase uv run python main.py | jq 'select(.level=="error")'

# 特定のユーザーのログ
docker compose exec polibase uv run python main.py | jq 'select(.user_id==123)'

# 遅い処理を検出（1000ms以上）
docker compose exec polibase uv run python main.py | jq 'select(.elapsed_ms > 1000)'
```

### ログの集計

```bash
# エラーレベル別の集計
docker compose exec polibase uv run python main.py | jq -r '.level' | sort | uniq -c

# モジュール別のエラー数
docker compose exec polibase uv run python main.py | jq 'select(.level=="error") | .logger' | sort | uniq -c
```

## 動作確認

構造化ログの動作確認スクリプトが用意されています：

```bash
# 動作確認スクリプトの実行
docker compose exec polibase uv run python scripts/verify_logging.py

# JSON形式で見やすく表示
docker compose exec polibase uv run python scripts/verify_logging.py | jq
```

## トラブルシューティング

### ログが出力されない

1. ログレベルを確認（DEBUGログはINFOレベルでは出力されない）
2. `setup_logging()`が呼ばれているか確認
3. ロガー名が正しいか確認

### ログが重複して出力される

1. `setup_logging()`が複数回呼ばれていないか確認
2. 標準のloggingモジュールと混在していないか確認

### 日本語が文字化けする

JSONフォーマットでは日本語はUnicodeエスケープされます。これは正常な動作です。
jqで表示する際は自動的にデコードされます。

## 今後の拡張予定

- OpenTelemetryとの統合によるメトリクス収集
- Sentryによる自動エラー追跡
- Grafanaダッシュボードでの可視化
- ログ集約システム（Loki）との連携

## 参考リンク

- [structlog公式ドキュメント](https://www.structlog.org/)
- [構造化ログのベストプラクティス](https://www.structlog.org/en/stable/recipes.html)
