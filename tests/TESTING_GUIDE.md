# Polibase テストガイド

このドキュメントは、Polibaseのテストスイートの構成と使用方法を説明します。

## 📁 ディレクトリ構成

```
tests/
├── docs/                        # テストドキュメント
│   ├── README.md               # ドキュメントインデックス
│   ├── TEST_MINUTES.md         # 議事録処理機能
│   ├── TEST_POLITICIANS.md     # 政治家情報抽出機能
│   ├── TEST_CONFERENCE_MEMBERS.md  # 会議体メンバー管理機能
│   ├── TEST_PARLIAMENTARY_GROUP.md # 議員団管理機能
│   ├── TEST_SCRAPING.md        # スクレイピング機能
│   └── TEST_DATABASE.md        # データベース管理機能
│
├── integration/                 # 統合テストスクリプト
│   ├── run_all_tests.sh        # 全テスト実行スクリプト
│   ├── system_health_check.py  # システムヘルスチェック
│   │
│   ├── minutes/                # 議事録処理テスト
│   │   ├── test_minutes_processing.sh
│   │   └── test_minutes_detailed.py
│   │
│   ├── politicians/            # 政治家情報テスト
│   │   ├── test_politicians_extraction.sh
│   │   └── test_politicians_detailed.py
│   │
│   ├── conference/             # 会議体メンバーテスト
│   │   ├── test_conference_members.sh
│   │   └── test_conference_detailed.py
│   │
│   ├── parliamentary/          # 議員団テスト
│   │   ├── test_parliamentary_group_extraction.sh
│   │   ├── test_parliamentary_group_detailed.py
│   │   ├── test_parliamentary_group_edge_cases.py
│   │   └── test_parliamentary_group_quick.py
│   │
│   ├── scraping/              # スクレイピングテスト
│   │   ├── test_scraping.sh
│   │   └── test_scraping_detailed.py
│   │
│   └── database/              # データベーステスト
│       ├── test_database_management.sh
│       ├── test_database_detailed.py
│       └── check_statistics.sql
│
└── unit/                       # ユニットテスト（既存）
    └── ...
```

## 🚀 クイックスタート

### 全機能のテスト実行

```bash
cd tests/integration
./run_all_tests.sh
```

実行時に以下のオプションが選択できます：
- 1) 基本テストのみ（推奨）
- 2) 詳細テストを含む
- 3) すべてのテスト

### 個別機能のテスト

```bash
# 議事録処理
cd tests/integration/minutes
./test_minutes_processing.sh

# 政治家情報抽出
cd tests/integration/politicians
./test_politicians_extraction.sh

# 会議体メンバー
cd tests/integration/conference
./test_conference_members.sh

# 議員団
cd tests/integration/parliamentary
./test_parliamentary_group_extraction.sh

# スクレイピング
cd tests/integration/scraping
./test_scraping.sh

# データベース管理
cd tests/integration/database
./test_database_management.sh
```

### システムヘルスチェック

```bash
docker compose exec polibase uv run python tests/integration/system_health_check.py
```

### データベース統計

```bash
docker compose exec postgres psql -U polibase_user -d polibase_db -f tests/integration/database/check_statistics.sql
```

## 📊 テストの種類

### 1. 基本テスト（.sh）
- 各機能の基本的な動作確認
- インタラクティブな実行
- 視覚的な結果表示

### 2. 詳細テスト（.py）
- プログラマティックなテスト
- エラーハンドリングの確認
- パフォーマンス測定
- データ品質チェック

### 3. エッジケーステスト
- 境界値のテスト
- 異常系の動作確認
- エラー処理の検証

## 🔍 テスト結果の見方

テスト実行後、以下の情報が表示されます：

1. **個別テスト結果**: 各テストの成功/失敗状態
2. **統計情報**: データ件数、処理時間など
3. **エラー詳細**: 失敗したテストの詳細情報
4. **総合判定**: 全体の成功/失敗数

## 🛠️ トラブルシューティング

### Docker関連
```bash
# コンテナ状態確認
docker compose ps

# ログ確認
docker compose logs -f polibase
```

### 環境変数
```bash
# 必須環境変数の確認
docker compose exec polibase env | grep -E "(GOOGLE_API_KEY|DATABASE_URL)"
```

### データベース接続
```bash
# 接続テスト
docker compose exec polibase uv run python -c "from src.config.database import test_connection; test_connection()"
```

## 📝 新しいテストの追加

1. 適切なディレクトリにテストスクリプトを作成
2. `tests/docs/`に対応するドキュメントを作成
3. `run_all_tests.sh`に新しいテストを追加
4. このガイドを更新

## 🤝 貢献

テストの改善や新しいテストケースの追加は歓迎します。プルリクエストを送る際は：

1. 既存のテストパターンに従う
2. ドキュメントを更新する
3. エラーケースも含める
4. 実行時間を考慮する
