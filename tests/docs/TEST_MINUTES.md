# 議事録処理機能 動作確認ガイド

このドキュメントでは、議事録処理機能（PDF→発言分割→発言者抽出→紐付け）の動作確認方法を説明します。

## 🔧 前提条件

- Docker Composeが起動していること
- GOOGLE_API_KEY（Gemini API）が設定されていること
- 会議情報がmeetingsテーブルに登録されていること

## 📋 処理フロー

1. **議事録分割**: PDFから発言を抽出し、conversationsテーブルに保存
2. **発言者抽出**: conversationsからspeakersを作成
3. **発言者紐付け**: conversationsとspeakersを紐付け
4. **政治家紐付け**: speakersとpoliticiansを紐付け

## 🚀 クイックスタート

### 基本的な動作確認
```bash
# 議事録処理テストスクリプトを実行
cd tests/integration/minutes
./test_minutes_processing.sh

# または個別に実行
# 1. 議事録分割（ローカルPDF）
docker compose exec polibase uv run polibase process-minutes

# 2. 議事録分割（GCSから特定の会議）
docker compose exec polibase uv run polibase process-minutes --meeting-id 123

# 3. 発言者抽出と紐付け
docker compose exec polibase uv run polibase extract-speakers

# 4. LLMベースの発言者-speaker紐付け
docker compose exec polibase uv run polibase update-speakers --use-llm
```

## 📊 データ確認

### 処理結果の確認
```sql
-- 最新の議事録
SELECT m.id, m.url, m.created_at,
       COUNT(c.id) as conversation_count
FROM minutes m
LEFT JOIN conversations c ON m.id = c.minutes_id
WHERE m.created_at >= CURRENT_TIMESTAMP - INTERVAL '1 day'
GROUP BY m.id, m.url, m.created_at
ORDER BY m.created_at DESC;

-- 発言者の統計
SELECT s.name, s.is_politician,
       COUNT(c.id) as speech_count
FROM speakers s
JOIN conversations c ON s.id = c.speaker_id
GROUP BY s.id, s.name, s.is_politician
ORDER BY speech_count DESC;

-- 未紐付けの発言
SELECT COUNT(*) as unlinked_count
FROM conversations
WHERE speaker_id IS NULL;
```

## 🔍 トラブルシューティング

### よくある問題

1. **PDFが見つからない**
   - dataディレクトリにPDFファイルを配置
   - または会議URLからスクレイピング

2. **Gemini APIエラー**
   - GOOGLE_API_KEYが正しく設定されているか確認
   - API利用制限に達していないか確認

3. **メモリ不足エラー**
   - 大きなPDFの場合は分割処理を検討
   - Docker Desktopのメモリ割り当てを増やす

## 📈 パフォーマンス指標

- 100ページのPDF: 約5-10分
- 発言者抽出: 1000発言あたり約1分
- LLMマッチング: 100名あたり約2-3分

## 🧪 詳細テスト

```bash
# 詳細な動作確認（Python）
docker compose exec polibase uv run python tests/integration/minutes/test_minutes_detailed.py

# エッジケーステスト
docker compose exec polibase uv run python tests/integration/minutes/test_minutes_edge_cases.py
```
