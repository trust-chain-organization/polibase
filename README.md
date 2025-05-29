# Polibase - 政治活動追跡アプリケーション

政治家の発言、議事録、公約などを体系的に管理・分析するためのアプリケーションです。

## 🗄️ テーブル構造
詳細なデータベース設計はこちらをご確認ください：
https://dbdocs.io/polibase/Polibase

## 🚀 環境構築手順

### 前提条件
- Docker & Docker Compose
- Python 3.13
- uv（Pythonパッケージマネージャー）

### 1. リポジトリのクローン
```bash
git clone https://github.com/trust-chain-organization/polibase.git
cd polibase
```

### 2. 環境変数の設定
```bash
# .envファイルを作成（必要に応じて設定を調整）
cp .env.example .env

# Google Gemini APIキーを設定（議事録処理に必要）
# .envファイルのGOOGLE_API_KEYを実際のAPIキーに置き換えてください
```

**重要**: Google Gemini APIキーは以下で取得できます：
- [Google AI Studio](https://aistudio.google.com/)でAPIキーを取得
- `.env`ファイルの`GOOGLE_API_KEY`に設定

### 3. Docker環境の起動
```bash
# PostgreSQLデータベースとアプリケーションを起動
docker compose up -d

# ログの確認
docker compose logs -f
```

### 4. Python依存関係のインストール（ローカル開発用）
```bash
# uvを使用して依存関係をインストール
uv sync
```

### 5. セットアップの確認
```bash
# セットアップが正常に完了したか確認
./test-setup.sh
```

## 🏃 使用方法

### アプリケーションの実行

#### 議事録分割処理
```bash
# Docker環境で実行
docker compose exec polibase uv run python -m src.main

# ローカル環境で実行
uv run python -m src.main
```

#### 政治家抽出処理
```bash
# Docker環境で実行
docker compose exec polibase uv run python -m src.main2

# ローカル環境で実行
uv run python -m src.main2
```

### テストの実行
```bash
# Docker環境で実行
docker compose exec polibase uv run pytest

# ローカル環境で実行
uv run pytest
```

## 🗃️ データベースの確認方法

### 1. PostgreSQLに接続
```bash
# Docker環境のPostgreSQLに接続
docker compose exec postgres psql -U polibase_user -d polibase_db
```

### 2. 基本的なSQLクエリ例
```sql
-- テーブル一覧を確認
\dt

-- 政党一覧を確認
SELECT * FROM political_parties;

-- 開催主体を確認
SELECT * FROM governing_bodies;

-- 会議体を確認
SELECT c.*, g.name as governing_body_name 
FROM conferences c 
JOIN governing_bodies g ON c.governing_body_id = g.id;

-- 発言データを確認（サンプルがある場合）
SELECT s.name as speaker_name, c.comment, c.sequence_number
FROM conversations c
JOIN speakers s ON c.speaker_id = s.id
LIMIT 10;
```

### 3. データベース接続テスト
```bash
# Pythonでデータベース接続をテスト
docker compose exec polibase uv run python -c "
from src.config.database import test_connection
test_connection()
"
```

## 💾 データベースの永続化とリセット

### データ永続化について

**デフォルト設定（永続化モード）**:
- `docker compose.yml`を使用すると、データベースは自動的に永続化されます
- `postgres_data`ボリュームにデータが保存され、コンテナを停止・再起動してもデータは保持されます

```bash
# 永続化モードで起動（デフォルト）
docker compose up -d

# コンテナを停止してもデータは保持される
docker compose down
docker compose up -d  # データがそのまま残る
```

**非永続化モード（一時的な使用）**:
- テストや一時的な使用の場合は、非永続化モードを使用できます
- コンテナ停止時にデータは全て削除されます

```bash
# 非永続化モードで起動
docker compose -f docker compose.temp.yml up -d

# または、既存のボリュームを使用せずに起動
docker compose down -v
docker compose up -d --renew-anon-volumes
```

### データベースのリセット

#### 完全リセット（推奨）
```bash
# 自動化されたリセットスクリプトを使用
./reset-database.sh
```

#### 手動リセット
```bash
# 1. コンテナとボリュームを完全削除
docker compose down -v

# 2. 再起動（初期データで復元）
docker compose up -d
```

### データのバックアップ・リストア

#### バックアップ作成
```bash
# データベース全体をバックアップ
./backup-database.sh backup

# バックアップファイル一覧を確認
./backup-database.sh list
```

#### リストア実行
```bash
# バックアップからリストア
./backup-database.sh restore database/backups/polibase_backup_20240529_123456.sql
```

#### 手動バックアップ・リストア
```bash
# 手動バックアップ
docker compose exec postgres pg_dump -U polibase_user polibase_db > backup.sql

# 手動リストア
docker compose exec -T postgres psql -U polibase_user -d polibase_db < backup.sql
```

## 📁 プロジェクト構成

```
polibase/
├── src/                          # メインアプリケーションコード
│   ├── config/                   # 設定ファイル
│   │   ├── database.py          # データベース接続設定
│   │   └── config.py            # アプリケーション設定
│   ├── minutes_divide_processor/ # 議事録分割処理
│   ├── politician_extract_processor/ # 政治家抽出処理
│   └── utils/                   # ユーティリティ関数
├── database/                    # データベース関連
│   ├── init.sql                # データベース初期化スクリプト
│   └── backups/                # データベースバックアップファイル
├── data/                       # データファイル
├── tests/                      # テストコード
├── docker compose.yml          # Docker Compose設定（永続化モード）
├── docker compose.temp.yml     # Docker Compose設定（非永続化モード）
├── Dockerfile                  # Dockerイメージ設定
├── reset-database.sh           # データベースリセットスクリプト
├── backup-database.sh          # データベースバックアップスクリプト
├── test-setup.sh              # セットアップテストスクリプト
├── pyproject.toml             # Python依存関係
└── polibase.dbml              # データベーススキーマ定義
```

## 🔧 開発用タスク

VS Codeでタスクを実行する場合：

- **テスト実行**: `Ctrl+Shift+P` → "Tasks: Run Task" → "test_polibase_project"
- **議事録分割処理**: `Ctrl+Shift+P` → "Tasks: Run Task" → "run_minutes_divide_processor"  
- **政治家抽出処理**: `Ctrl+Shift+P` → "Tasks: Run Task" → "run_politician_extract_processor"

## 🛠️ トラブルシューティング

### Docker関連のエラー

#### ポートが既に使用されている場合
```bash
# 使用中のポートを確認
lsof -i :5432
lsof -i :8000

# Docker Composeを再起動
docker compose down
docker compose up -d
```

#### データベース接続エラー
```bash
# PostgreSQLコンテナのログを確認
docker compose logs postgres

# データベース接続テスト
./test-setup.sh
```

#### コンテナのリセット
```bash
# 全てのコンテナとボリュームを削除して再作成
docker compose down -v
docker compose up -d
```

#### データベースの問題

**データが破損した場合**:
```bash
# データベースを完全リセット
./reset-database.sh
```

**古いデータを残したい場合**:
```bash
# バックアップを作成してからリセット
./backup-database.sh backup
./reset-database.sh
```

**ディスク容量不足**:
```bash
# 不要なDockerボリュームを削除
docker volume prune

# 古いイメージを削除
docker image prune -a
```

### Python環境の問題

#### uvが見つからない場合
```bash
# uvをインストール
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

#### 依存関係の問題
```bash
# 依存関係を再インストール
uv sync --reinstall
```

## 🗂️ データの流れ

1. **議事録PDFの処理**: `src/main.py` - 議事録を発言単位に分割
2. **政治家情報の抽出**: `src/main2.py` - 発言から政治家情報を抽出
3. **データベース保存**: 抽出された情報をPostgreSQLに保存
4. **分析・検索**: 蓄積されたデータから政治活動を分析

## 🚀 クイックリファレンス

### よく使うコマンド

```bash
# 🏗️ 初期セットアップ
cp .env.example .env
docker compose up -d
./test-setup.sh

# 🔄 通常の起動・停止
docker compose up -d      # バックグラウンド起動
docker compose down       # 停止（データは保持）
docker compose logs -f    # ログ確認

# 💾 データベース管理
./backup-database.sh backup           # バックアップ作成
./backup-database.sh list             # バックアップ一覧
./reset-database.sh                   # データベースリセット

# 🏃 アプリケーション実行
docker compose exec polibase uv run python -m src.main   # 議事録分割
docker compose exec polibase uv run python -m src.main2  # 政治家抽出
docker compose exec polibase uv run pytest              # テスト実行

# 🗃️ データベース操作
docker compose exec postgres psql -U polibase_user -d polibase_db  # DB接続
```

### 開発モード

```bash
# 🔧 非永続化モード（テスト用）
docker compose -f docker compose.temp.yml up -d

# 🐛 デバッグモード
docker compose up          # フォアグラウンド実行
docker compose exec polibase bash  # コンテナ内でshell実行
```

# 開発環境の生成AIの設定
https://code.visualstudio.com/docs/copilot/copilot-customization

- .github/prompts/hogehoge.prompt.md
  - chat/editで使えるカスタムのプロンプトを配置

- .vscode/settings.json
    - 開発環境の設定を記載
    - このプロジェクト用のMCPの設定を記載
- .github/copilot-instructions.md
  - エージェントが従う作業フローの指示を記載
    - プロダクトマネージャー業務の指示
        - product_management業務の参照ドキュメント
            - product_management_reference/product_goal.md
            - product_management_reference/daily_task.md
    - コード修正業務の指示
- このプロジェクト用のcopilotの作業時の設定を記載(copilot-instructions.mdを継承)
    - .vscode/code-style.md
        - コード生成時のルール
    - .vscode/test-style.md
        - テスト生成時のルール
    - .vscode/review-style.md
        - レビュー時のルール
    - .vscode/commit-message-style.md
        - コミットメッセージの生成時のルール
    - .vscode/pull-request-style.md
        - pull requestの生成時のルール
