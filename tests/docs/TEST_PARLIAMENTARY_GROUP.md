# 議員団メンバー抽出機能 動作検証ガイド

このドキュメントでは、議員団メンバー抽出機能の動作検証方法を説明します。

## 🔧 前提条件

- Docker Composeが起動していること
- データベースが正しくセットアップされていること
- 少なくとも1つの議員団がURLと共に登録されていること

## 📝 テストスクリプト一覧

### 1. `test_parliamentary_group_extraction.sh`
**基本的な動作検証用Bashスクリプト**

3段階処理（抽出→マッチング→作成）の基本的な動作を確認します。

```bash
# 実行方法
./test_parliamentary_group_extraction.sh

# 実行内容:
# 1. 環境チェック
# 2. 議員団一覧表示
# 3. ステップ1: メンバー抽出
# 4. ステップ2: 政治家マッチング
# 5. ステップ3: メンバーシップ作成
# 6. 最終状態確認
```

### 2. `test_parliamentary_group_detailed.py`
**詳細な動作検証用Pythonスクリプト**

より詳細な情報表示とテーブル形式での結果確認が可能です。

```bash
# 全議員団をテスト（URLがある最初の議員団を使用）
docker compose exec polibase uv run python test_parliamentary_group_detailed.py

# 特定の議員団をテスト（議員団ID指定）
docker compose exec polibase uv run python test_parliamentary_group_detailed.py 10
```

**表示内容:**
- 議員団一覧（テーブル形式）
- 抽出されたメンバー詳細
- マッチング結果と信頼度
- 作成されたメンバーシップ一覧

### 3. `test_parliamentary_edge_cases.py`
**エッジケーステスト用スクリプト**

エラーケースや特殊な状況での動作を検証します。

```bash
# 実行方法
docker compose exec polibase uv run python test_parliamentary_edge_cases.py

# テスト内容:
# - URLなし議員団の処理
# - 重複抽出の防止
# - マッチしない場合の処理
# - 空レスポンスの処理
# - 並行処理の動作
```

## 🚀 クイックスタート

### 基本的な動作確認
```bash
# 1. 基本テストを実行
./test_parliamentary_group_extraction.sh

# 2. より詳細な情報を確認したい場合
docker compose exec polibase uv run python test_parliamentary_group_detailed.py
```

### 個別コマンドでの確認
```bash
# 議員団一覧を確認
docker compose exec polibase uv run polibase list-parliamentary-groups

# 抽出状況を確認
docker compose exec polibase uv run polibase group-member-status

# 特定の議員団のメンバーを抽出
docker compose exec polibase uv run polibase extract-group-members --group-id 10

# マッチングを実行
docker compose exec polibase uv run polibase match-group-members --group-id 10

# メンバーシップを作成
docker compose exec polibase uv run polibase create-group-memberships --group-id 10
```

## 📊 データベース確認

### 抽出されたメンバーの確認
```sql
-- 抽出状況のサマリー
SELECT
    pg.name as 議員団名,
    COUNT(epgm.id) as 抽出数,
    COUNT(CASE WHEN epgm.matching_status = 'matched' THEN 1 END) as マッチ済み,
    COUNT(CASE WHEN epgm.matching_status = 'needs_review' THEN 1 END) as 要確認,
    COUNT(CASE WHEN epgm.matching_status = 'no_match' THEN 1 END) as マッチなし
FROM parliamentary_groups pg
LEFT JOIN extracted_parliamentary_group_members epgm
    ON pg.id = epgm.parliamentary_group_id
GROUP BY pg.id, pg.name
ORDER BY pg.name;

-- 詳細データ
SELECT * FROM extracted_parliamentary_group_members
WHERE parliamentary_group_id = 10
ORDER BY matching_status, extracted_name;
```

### メンバーシップの確認
```sql
-- 現在のメンバーシップ
SELECT
    pg.name as 議員団名,
    p.name as 政治家名,
    pgm.role as 役職,
    pgm.start_date as 開始日
FROM parliamentary_group_memberships pgm
JOIN parliamentary_groups pg ON pgm.parliamentary_group_id = pg.id
JOIN politicians p ON pgm.politician_id = p.id
WHERE pgm.end_date IS NULL
ORDER BY pg.name, p.name;
```

## 🔍 トラブルシューティング

### よくある問題と解決方法

1. **「URLが設定されていません」エラー**
   - Streamlit UIまたはデータベースで議員団のURLを設定してください
   ```sql
   UPDATE parliamentary_groups
   SET url = 'https://example.com/members'
   WHERE id = 10;
   ```

2. **マッチングが0件の場合**
   - 政治家マスタにデータが登録されているか確認
   - 政党の議員情報をスクレイピングで取得
   ```bash
   docker compose exec polibase uv run polibase scrape-politicians --party-id 2
   ```

3. **重複エラーが発生する場合**
   - 既存データをクリアして再実行
   ```sql
   DELETE FROM extracted_parliamentary_group_members
   WHERE parliamentary_group_id = 10;
   ```

## 📈 パフォーマンステスト

大量データでのテスト方法：

```bash
# 複数の議員団を並行処理
docker compose exec polibase uv run polibase extract-group-members --all-groups

# 処理時間の計測
time docker compose exec polibase uv run polibase match-group-members
```

## 🎯 期待される結果

正常に動作している場合：

1. **抽出ステップ**: URLからメンバー情報が抽出される
2. **マッチングステップ**: 既存の政治家と名前でマッチング（信頼度付き）
3. **作成ステップ**: マッチしたメンバーのメンバーシップが作成される

各ステップは独立して実行可能で、途中で停止しても再開できます。
