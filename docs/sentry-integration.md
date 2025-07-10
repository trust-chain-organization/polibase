# Sentry Error Tracking Integration

Polibaseでは、エラー追跡とパフォーマンス監視のためにSentryを統合しています。

## 概要

Sentryは以下の機能を提供します：
- 自動エラーキャプチャ
- パフォーマンス監視
- エラーの集約と傾向分析
- アラート設定
- デバッグ情報の収集

## セットアップ

### 1. 環境変数の設定

`.env`ファイルに以下の環境変数を設定します：

```bash
# Sentry Error Tracking Configuration
SENTRY_DSN=https://your-dsn@sentry.io/project-id  # Sentry DSN（必須）
SENTRY_TRACES_SAMPLE_RATE=0.1  # パフォーマンス監視のサンプルレート (0.0-1.0)
SENTRY_PROFILES_SAMPLE_RATE=0.1  # プロファイリングのサンプルレート (0.0-1.0)
SENTRY_RELEASE=polibase@0.1.0  # リリースバージョン
```

### 2. セルフホスト版Sentryの使用

プライバシーの観点から、セルフホスト版のSentryを推奨します：

```bash
# Docker Composeでセルフホスト版Sentryを起動
git clone https://github.com/getsentry/self-hosted.git
cd self-hosted
./install.sh
docker compose up -d
```

## 機能と統合

### 1. 自動エラーキャプチャ

すべてのエラーは自動的にSentryに送信されます：

```python
from src.common.logging import get_logger

logger = get_logger(__name__)

try:
    # 処理
    pass
except Exception as e:
    logger.error("処理エラーが発生しました", exc_info=True)
    # エラーは自動的にSentryに送信されます
```

### 2. Structlogとの統合

structlogのERROR以上のログは自動的にSentryに送信されます：

```python
logger.error("重大なエラー", user_id=123, operation="データ処理")
# このログはSentryにも送信され、追加のコンテキストが含まれます
```

### 3. SQLAlchemyエラーの自動キャプチャ

SQLAlchemyのエラーは自動的にキャプチャされます：

```python
# SQLAlchemyのエラーは自動的にSentryに送信されます
session.query(Meeting).filter_by(id=999999).one()  # RecordNotFoundError
```

### 4. パフォーマンス監視

#### 基本的な使用方法

```python
from src.config.sentry import monitor_performance

@monitor_performance(op="task", description="議事録処理")
def process_minutes():
    # 処理時間が自動的に記録されます
    pass
```

#### データベースクエリの監視

```python
from src.config.sentry import monitor_db_query

@monitor_db_query("fetch_meetings_by_date")
def get_meetings_by_date(date):
    return session.query(Meeting).filter_by(date=date).all()
```

#### LLM呼び出しの監視

```python
from src.config.sentry import monitor_llm_call

@monitor_llm_call(model="gemini-2.0-flash")
def call_gemini_api(prompt):
    # API呼び出し時間とモデル情報が記録されます
    return llm.invoke(prompt)
```

#### Webスクレイピングの監視

```python
from src.config.sentry import monitor_web_scraping

@monitor_web_scraping(url="https://example.com")
def scrape_website():
    # スクレイピング処理時間が記録されます
    pass
```

### 5. カスタムコンテキストの追加

```python
from src.config.sentry import set_context, set_tag, add_breadcrumb

# コンテキストの設定
set_context("meeting", {
    "id": meeting_id,
    "date": meeting_date,
    "conference": conference_name
})

# タグの設定（フィルタリング用）
set_tag("operation", "minutes_processing")
set_tag("conference_type", "city_council")

# ブレッドクラムの追加（デバッグ用）
add_breadcrumb(
    message="議事録処理を開始",
    category="processing",
    data={"file_path": pdf_path}
)
```

### 6. 手動でのエラー送信

```python
from src.config.sentry import capture_exception, capture_message

try:
    risky_operation()
except SpecificError as e:
    # 特定のエラーをキャプチャ
    capture_exception(e, extra={"custom_data": "value"})

# メッセージの送信
capture_message("重要なイベントが発生", level="warning")
```

## データプライバシー

### 1. 個人情報の保護

- `send_default_pii=False`に設定されており、個人情報は送信されません
- エラーメッセージは自動的にサニタイズされます

### 2. サニタイズされる情報

以下の情報は自動的に削除またはマスクされます：
- APIキー（GOOGLE_API_KEY等）
- データベースURL
- パスワード、トークン、シークレット

### 3. フィルタリング

```python
# before_send_filterで特定のエラーを除外
def before_send_filter(event, hint):
    # KeyboardInterruptは送信しない
    if hint.get("exc_info") and hint["exc_info"][0] is KeyboardInterrupt:
        return None
    return event
```

## ダッシュボードの活用

### 1. エラーの確認

Sentryダッシュボードで以下を確認できます：
- エラーの発生頻度
- エラーの影響を受けたユーザー数
- エラーのスタックトレース
- エラー発生時のコンテキスト

### 2. パフォーマンスの確認

- トランザクションの処理時間
- 遅いデータベースクエリ
- LLM APIの応答時間
- N+1問題の検出

### 3. アラート設定

以下のアラートを設定できます：
- エラー率の閾値超過
- 新規エラータイプの発生
- パフォーマンスの劣化

## トラブルシューティング

### Sentryにエラーが送信されない場合

1. `SENTRY_DSN`が正しく設定されているか確認
2. ネットワーク接続を確認
3. ログレベルがERROR以上になっているか確認

### パフォーマンスデータが記録されない場合

1. `SENTRY_TRACES_SAMPLE_RATE`が0より大きいか確認
2. デコレータが正しく適用されているか確認

### デバッグモード

```bash
# デバッグモードで詳細ログを表示
DEBUG=true SENTRY_DSN=... python -m src.cli
```

## ベストプラクティス

1. **エラーハンドリング**: 予期しないエラーはキャッチせず、Sentryに送信
2. **コンテキスト追加**: エラー発生時の状況を理解しやすくするため、適切なコンテキストを追加
3. **タグ活用**: フィルタリングしやすいよう、適切なタグを設定
4. **パフォーマンス監視**: 重要な処理にはパフォーマンス監視を追加
5. **定期的な確認**: Sentryダッシュボードを定期的に確認し、問題を早期発見
