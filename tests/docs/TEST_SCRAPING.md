# スクレイピング機能 動作確認ガイド

このドキュメントでは、議事録Webスクレイピング機能の動作確認方法を説明します。

## 🔧 前提条件

- Docker Composeが起動していること
- インターネット接続があること
- （オプション）GCS認証が設定されていること
- （オプション）GCS_BUCKET_NAMEが.envに設定されていること

## 📋 対応サイト

1. **kaigiroku.net**: 多くの地方議会が使用するシステム
2. **kokkai.ndl.go.jp**: 国会会議録検索システム
3. **その他**: 個別対応可能

## 🚀 クイックスタート

### 基本的な動作確認
```bash
# スクレイピングテストスクリプトを実行
cd tests/integration/scraping
./test_scraping.sh

# または個別に実行
# 1. 単一議事録のスクレイピング
docker compose exec polibase uv run polibase scrape-minutes "https://example.com/minutes.html"

# 2. GCSアップロード付きスクレイピング
docker compose exec polibase uv run polibase scrape-minutes "URL" --upload-to-gcs

# 3. バッチスクレイピング（kaigiroku.net）
docker compose exec polibase uv run polibase batch-scrape --tenant kyoto
docker compose exec polibase uv run polibase batch-scrape --tenant osaka --upload-to-gcs
```

## 📊 データ確認

### スクレイピング結果の確認
```sql
-- 最近のスクレイピング結果
SELECT m.id, m.date, m.url,
       m.gcs_pdf_uri, m.gcs_text_uri,
       gb.name as governing_body,
       c.name as conference
FROM meetings m
JOIN conferences c ON m.conference_id = c.id
JOIN governing_bodies gb ON c.governing_body_id = gb.id
WHERE m.created_at >= CURRENT_TIMESTAMP - INTERVAL '1 day'
ORDER BY m.created_at DESC;

-- GCSアップロード状況
SELECT COUNT(*) as total_meetings,
       COUNT(gcs_pdf_uri) as with_pdf,
       COUNT(gcs_text_uri) as with_text
FROM meetings
WHERE date >= '2024-01-01';
```

## 🔍 トラブルシューティング

### よくある問題

1. **接続タイムアウト**
   - ネットワーク接続を確認
   - サイトがメンテナンス中でないか確認
   - リトライ機能は自動で3回まで

2. **GCSアップロードエラー**
   ```bash
   # 認証設定
   gcloud auth application-default login

   # バケット確認
   gsutil ls gs://your-bucket-name/
   ```

3. **文字化け**
   - 自動的にエンコーディングを検出
   - 手動で確認: `file -i scraped_file.txt`

## 📈 パフォーマンス指標

- 単一議事録: 5-10秒
- PDF生成: 10-30秒（ページ数による）
- バッチ処理: 10件で約2-3分
- GCSアップロード: ファイルサイズによる

## 🧪 詳細テスト

```bash
# 詳細な動作確認（Python）
docker compose exec polibase uv run python tests/integration/scraping/test_scraping_detailed.py

# 特定サイトのテスト
docker compose exec polibase uv run python tests/integration/scraping/test_kaigiroku.py
docker compose exec polibase uv run python tests/integration/scraping/test_kokkai.py

# GCS統合テスト
docker compose exec polibase uv run python tests/integration/scraping/test_gcs_integration.py
```

## 📝 スクレイピング設定

### バッチスクレイピング対象
```python
# 現在対応している自治体（kaigiroku.net）
SUPPORTED_TENANTS = [
    "kyoto",    # 京都府
    "osaka",    # 大阪府
    # 今後追加予定
]
```

### GCSファイル構造
```
gs://your-bucket/scraped/
├── 2024/
│   ├── 01/
│   │   ├── 15/
│   │   │   ├── kyoto_12345.pdf
│   │   │   └── kyoto_12345.txt
```

## 🔄 定期実行設定

```bash
# Cronジョブ例（毎日午前3時に実行）
0 3 * * * docker compose exec -T polibase uv run polibase batch-scrape --tenant kyoto --upload-to-gcs

# 複数自治体の並列実行
parallel -j 2 docker compose exec -T polibase uv run polibase batch-scrape --tenant {} --upload-to-gcs ::: kyoto osaka
```

## 🌐 新規サイト対応

新しいスクレイパーを追加する場合：
1. `src/web_scraper/`に新規スクレイパークラス作成
2. `BaseScraperInterface`を実装
3. `scraper_service.py`に登録
