# Polibase 動作確認ガイド

このディレクトリには、Polibaseの各機能の動作確認方法をまとめたドキュメントが含まれています。

## 📚 機能別ガイド

### 1. [議事録処理機能](TEST_MINUTES.md)
- PDF議事録の分割処理
- 発言者の抽出と紐付け
- LLMを使用した高度なマッチング

### 2. [政治家情報抽出機能](TEST_POLITICIANS.md)
- 政党Webサイトからの議員情報スクレイピング
- ページネーション対応
- 重複チェックと更新処理

### 3. [会議体メンバー管理機能](TEST_CONFERENCE_MEMBERS.md)
- 3段階処理（抽出→マッチング→作成）
- LLMによる曖昧マッチング
- 信頼度ベースのステータス管理

### 4. [議員団管理機能](TEST_PARLIAMENTARY_GROUP.md)
- 議員団メンバーの自動抽出
- 既存政治家とのマッチング
- メンバーシップの作成と管理

### 5. [スクレイピング機能](TEST_SCRAPING.md)
- kaigiroku.net対応
- 国会会議録システム対応
- GCS統合とバッチ処理

### 6. [データベース管理機能](TEST_DATABASE.md)
- バックアップとリストア
- マイグレーション管理
- GCS統合バックアップ

## 🚀 クイックスタート

### 全機能の基本テスト
```bash
# 統合テストスクリプトの実行
cd tests/integration
./run_all_tests.sh

# または機能別に実行
cd tests/integration/minutes && ./test_minutes_processing.sh
cd tests/integration/politicians && ./test_politicians_extraction.sh
cd tests/integration/conference && ./test_conference_members.sh
cd tests/integration/parliamentary && ./test_parliamentary_group_extraction.sh
cd tests/integration/scraping && ./test_scraping.sh
cd tests/integration/database && ./test_database_management.sh
```

## 📊 システム全体の状態確認

```bash
# システムヘルスチェック
docker compose exec polibase uv run python tests/integration/system_health_check.py

# データベース統計
docker compose exec postgres psql -U polibase_user -d polibase_db -f tests/integration/database/check_statistics.sql
```

## 🧪 テストの種類

### 基本テスト
- 各機能の正常動作確認
- 主要なユースケースのカバー

### 詳細テスト
- エッジケースの検証
- エラーハンドリングの確認
- パフォーマンス測定

### 統合テスト
- 機能間の連携確認
- エンドツーエンドのワークフロー

## 📝 新機能のテスト追加

新しい機能のテストを追加する場合：

1. `tests/docs/TEST_[FEATURE].md`を作成
2. `tests/integration/[feature]/`ディレクトリを作成
3. 基本テストスクリプト（.sh）を作成
4. 詳細テストスクリプト（.py）を作成
5. このREADMEに追加

## 🔍 トラブルシューティング共通事項

### Docker関連
```bash
# コンテナの状態確認
docker compose ps

# ログ確認
docker compose logs -f polibase
docker compose logs -f postgres

# リソース使用状況
docker stats
```

### 環境変数
```bash
# 必須環境変数の確認
docker compose exec polibase env | grep -E "(GOOGLE_API_KEY|DATABASE_URL|GCS_)"
```

### ネットワーク
```bash
# 内部ネットワーク確認
docker compose exec polibase ping postgres
docker compose exec polibase curl -I https://www.google.com
```

## 📈 パフォーマンスベンチマーク

```bash
# 全機能のベンチマーク実行
docker compose exec polibase uv run python tests/integration/run_benchmarks.py

# 結果の確認
cat tests/integration/benchmark_results.json
```

## 🤝 貢献方法

テストの改善や新しいテストケースの追加は歓迎します：

1. 既存のテストパターンに従う
2. ドキュメントを更新
3. エラーケースも含める
4. 実行時間を記録
