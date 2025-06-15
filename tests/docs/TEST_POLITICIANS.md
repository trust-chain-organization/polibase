# 政治家情報抽出機能 動作確認ガイド

このドキュメントでは、政党Webサイトからの政治家情報抽出機能の動作確認方法を説明します。

## 🔧 前提条件

- Docker Composeが起動していること
- GOOGLE_API_KEY（Gemini API）が設定されていること
- political_partiesテーブルにmembers_list_urlが設定されていること
- Playwrightがインストールされていること

## 📋 処理フロー

1. **URL設定**: 政党の議員一覧ページURLを設定
2. **Webスクレイピング**: PlaywrightでHTMLを取得
3. **LLM抽出**: Gemini APIで政治家情報を構造化抽出
4. **データ保存**: politiciansテーブルに保存（重複チェック付き）

## 🚀 クイックスタート

### 基本的な動作確認
```bash
# 政治家情報抽出テストスクリプトを実行
cd tests/integration/politicians
./test_politicians_extraction.sh

# または個別に実行
# 1. すべての政党から抽出
docker compose exec polibase uv run polibase scrape-politicians --all-parties

# 2. 特定の政党から抽出
docker compose exec polibase uv run polibase scrape-politicians --party-id 2

# 3. ドライラン（実際には保存しない）
docker compose exec polibase uv run polibase scrape-politicians --all-parties --dry-run
```

## 📊 データ確認

### 政党別の議員数
```sql
-- 政党別議員数
SELECT pp.name as party_name,
       COUNT(p.id) as member_count,
       pp.members_list_url
FROM political_parties pp
LEFT JOIN politicians p ON pp.id = p.political_party_id
GROUP BY pp.id, pp.name, pp.members_list_url
ORDER BY member_count DESC;

-- 最近追加された政治家
SELECT p.name, pp.name as party_name,
       p.position, p.prefecture, p.created_at
FROM politicians p
JOIN political_parties pp ON p.political_party_id = pp.id
WHERE p.created_at >= CURRENT_TIMESTAMP - INTERVAL '1 day'
ORDER BY p.created_at DESC
LIMIT 20;

-- 重複チェック
SELECT name, political_party_id, COUNT(*) as count
FROM politicians
GROUP BY name, political_party_id
HAVING COUNT(*) > 1;
```

## 🔍 トラブルシューティング

### よくある問題

1. **URLが設定されていない**
   ```sql
   -- StreamlitまたはSQLで設定
   UPDATE political_parties
   SET members_list_url = 'https://example.com/members'
   WHERE id = 1;
   ```

2. **Playwright起動エラー**
   ```bash
   # 依存関係のインストール
   docker compose exec polibase uv run playwright install-deps
   docker compose exec polibase uv run playwright install chromium
   ```

3. **ページネーション対応**
   - 自動的に「次へ」リンクを検出
   - 最大20ページまで取得

## 📈 パフォーマンス指標

- 1政党（100名）: 約2-3分
- 全政党（500名）: 約10-15分
- ページ読み込み: 2秒のウェイト

## 🧪 詳細テスト

```bash
# 詳細な動作確認（Python）
docker compose exec polibase uv run python tests/integration/politicians/test_politicians_detailed.py

# 特定政党のテスト
docker compose exec polibase uv run python tests/integration/politicians/test_specific_party.py --party-id 2
```

## 📝 設定可能な政党URL例

```sql
-- 自民党
UPDATE political_parties SET members_list_url = 'https://www.jimin.jp/member/' WHERE name = '自由民主党';

-- 立憲民主党
UPDATE political_parties SET members_list_url = 'https://cdp-japan.jp/members/all' WHERE name = '立憲民主党';

-- 公明党
UPDATE political_parties SET members_list_url = 'https://www.komei.or.jp/member/' WHERE name = '公明党';
```
