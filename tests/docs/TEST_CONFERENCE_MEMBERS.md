# 会議体メンバー管理機能 動作確認ガイド

このドキュメントでは、会議体（議会・委員会）メンバーの抽出・マッチング・管理機能の動作確認方法を説明します。

## 🔧 前提条件

- Docker Composeが起動していること
- GOOGLE_API_KEY（Gemini API）が設定されていること
- conferencesテーブルにmembers_introduction_urlが設定されていること
- politiciansテーブルに既存の政治家データがあること

## 📋 処理フロー（3段階処理）

1. **メンバー抽出**: URLから議員情報を抽出してextracted_conference_membersに保存
2. **政治家マッチング**: 抽出データを既存政治家とLLMでマッチング
3. **所属作成**: マッチング済みデータからpolitician_affiliationsを作成

## 🚀 クイックスタート

### 基本的な動作確認
```bash
# 会議体メンバー管理テストスクリプトを実行
cd tests/integration/conference
./test_conference_members.sh

# または個別に実行
# 1. ステップ1: メンバー抽出
docker compose exec polibase uv run polibase extract-conference-members --conference-id 185

# 2. ステップ2: 政治家マッチング
docker compose exec polibase uv run polibase match-conference-members --conference-id 185

# 3. ステップ3: 所属作成
docker compose exec polibase uv run polibase create-affiliations --conference-id 185 --start-date 2024-01-01

# 状況確認
docker compose exec polibase uv run polibase member-status --conference-id 185
```

## 📊 データ確認

### 抽出・マッチング状況
```sql
-- 会議体別の抽出状況
SELECT c.name as conference_name,
       c.members_introduction_url,
       COUNT(ecm.id) as extracted_count,
       COUNT(CASE WHEN ecm.matching_status = 'matched' THEN 1 END) as matched,
       COUNT(CASE WHEN ecm.matching_status = 'needs_review' THEN 1 END) as needs_review,
       COUNT(CASE WHEN ecm.matching_status = 'no_match' THEN 1 END) as no_match
FROM conferences c
LEFT JOIN extracted_conference_members ecm ON c.id = ecm.conference_id
WHERE c.members_introduction_url IS NOT NULL
GROUP BY c.id, c.name, c.members_introduction_url;

-- マッチング詳細
SELECT ecm.extracted_name, ecm.extracted_role,
       ecm.matching_status, ecm.matching_confidence,
       p.name as matched_politician_name
FROM extracted_conference_members ecm
LEFT JOIN politicians p ON ecm.matched_politician_id = p.id
WHERE ecm.conference_id = 185
ORDER BY ecm.matching_status, ecm.extracted_name;

-- 現在の所属状況
SELECT c.name as conference_name,
       p.name as politician_name,
       pa.role, pa.start_date
FROM politician_affiliations pa
JOIN politicians p ON pa.politician_id = p.id
JOIN conferences c ON pa.conference_id = c.id
WHERE pa.end_date IS NULL
ORDER BY c.name, p.name;
```

## 🔍 トラブルシューティング

### よくある問題

1. **URLが設定されていない**
   - Streamlit UIの「会議体管理」→「議員紹介URL管理」で設定
   - またはSQLで直接設定

2. **マッチング率が低い**
   - 先に政治家マスタを充実させる（scrape-politicians実行）
   - needs_reviewのデータを手動で確認

3. **重複所属の防止**
   - 同一期間の重複所属は自動的にスキップ
   - end_dateを設定して過去の所属を終了

## 📈 パフォーマンス指標

- 抽出: 50名で約1-2分
- マッチング: 100名で約3-5分（LLM処理）
- マッチング精度:
  - 完全一致: 95%以上
  - 表記ゆれ対応: 80%以上

## 🧪 詳細テスト

```bash
# 詳細な動作確認（Python）
docker compose exec polibase uv run python tests/integration/conference/test_conference_detailed.py

# 特定会議体のテスト
docker compose exec polibase uv run python tests/integration/conference/test_specific_conference.py --conference-id 185

# マッチング精度テスト
docker compose exec polibase uv run python tests/integration/conference/test_matching_accuracy.py
```

## 📝 マッチングステータス

- **matched** (≥0.7): 自動で所属作成可能
- **needs_review** (0.5-0.7): 手動確認推奨
- **no_match** (<0.5): 新規政治家の可能性
- **pending**: 未処理

## 🔄 再実行・リセット

```bash
# 強制再抽出
docker compose exec polibase uv run polibase extract-conference-members --conference-id 185 --force

# 全会議体を処理
docker compose exec polibase uv run polibase extract-conference-members --force
docker compose exec polibase uv run polibase match-conference-members
docker compose exec polibase uv run polibase create-affiliations --start-date 2024-01-01
```
