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

#### 議事録分割処理（発言抽出）
```bash
# Docker環境で実行
docker compose exec polibase uv run python -m src.main

# ローカル環境で実行
uv run python -m src.main
```
議事録PDFファイルを読み込み、発言単位に分割してデータベースに保存します。

#### 政治家情報抽出処理（発言者抽出）
```bash
# Docker環境で実行
docker compose exec polibase uv run python -m src.main2

# ローカル環境で実行
uv run python -m src.main2
```
議事録から政治家（発言者）の情報を抽出してデータベースに保存します。

#### LLMベース発言者マッチング処理
```bash
# Docker環境で実行
docker compose exec polibase uv run python update_speaker_links_llm.py

# ローカル環境で実行
uv run python update_speaker_links_llm.py
```
LLMを活用したfuzzy matchingにより、議事録の発言(`conversations.speaker_name`)と発言者マスタ(`speakers.name`)の間で高精度なマッチングを実行し、未紐付けの会話に適切な発言者IDを自動で紐付けます。

**特徴:**
- ルールベース + LLMベースのハイブリッドマッチング
- 表記揺れや記号の有無に対応した高精度マッチング
- インタラクティブな確認機能付き
- 詳細な処理結果レポート

**必要な環境変数:**
- `GOOGLE_API_KEY`: Google Gemini APIキー（.envファイルに設定）

### テストの実行
```bash
# Docker環境で実行
docker compose exec polibase uv run pytest

# ローカル環境で実行
uv run pytest
```

## 🗃️ データベースの確認方法

### マスターデータについて

**開催主体（governing_bodies）と会議体（conferences）**は基本的に増減しない固定的なマスターデータとして扱います。これらのデータは以下のSEEDファイルで管理しています：

- `database/seed_governing_bodies.sql`: 日本国、47都道府県、主要市町村（政令指定都市、東京23区等）
- `database/seed_conferences.sql`: 国会・各委員会、都道府県議会、市区議会
- `database/seed_political_parties.sql`: 主要政党、地域政党、過去の政党

これらのマスターデータは、システム初期化時に自動的に投入され、アプリケーション運用中は基本的に変更されません。

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

-- 発言データと発言者の紐付け状況を確認
SELECT 
    COUNT(*) as total_conversations,
    COUNT(speaker_id) as linked_conversations,
    COUNT(*) - COUNT(speaker_id) as unlinked_conversations
FROM conversations;

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
│   ├── common/                   # 共通機能
│   │   ├── app_logic.py         # アプリケーション共通ロジック
│   │   └── database_utils.py    # データベース共通処理
│   ├── minutes_divide_processor/ # 議事録分割処理
│   ├── politician_extract_processor/ # 政治家抽出処理
│   ├── database/                 # データベースリポジトリ
│   └── utils/                   # ユーティリティ関数
├── database/                    # データベース関連
│   ├── init.sql                # データベース初期化スクリプト
│   └── backups/                # データベースバックアップファイル
├── scripts/                     # 管理スクリプト
│   ├── backup-database.sh      # データベースバックアップスクリプト
│   ├── reset-database.sh       # データベースリセットスクリプト
│   ├── test-setup.sh           # セットアップテストスクリプト
│   └── setup_database.sh       # データベースセットアップスクリプト
├── data/                       # データファイル
├── tests/                      # テストコード
├── docker compose.yml          # Docker Compose設定（永続化モード）
├── docker compose.temp.yml     # Docker Compose設定（非永続化モード）
├── Dockerfile                  # Dockerイメージ設定
├── backup-database.sh          # → scripts/backup-database.sh (シンボリックリンク)
├── reset-database.sh           # → scripts/reset-database.sh (シンボリックリンク)
├── test-setup.sh              # → scripts/test-setup.sh (シンボリックリンク)
├── update_speaker_links.py     # 発言者紐付け更新スクリプト（レガシー）
├── update_speaker_links_llm.py # LLMベース発言者マッチングスクリプト
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

1. **議事録PDFの処理**: `src/main.py` - 議事録を発言単位に分割してデータベースに保存
2. **政治家情報の抽出**: `src/main2.py` - 発言から政治家情報を抽出してデータベースに保存
3. **発言者マッチング**: `update_speaker_links_llm.py` - LLMを活用して発言と発言者を高精度でマッチング
4. **データベース保存**: 抽出・マッチングされた情報をPostgreSQLに保存
5. **分析・検索**: 蓄積されたデータから政治活動を分析

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
docker compose exec polibase uv run python -m src.main   # 議事録分割（発言抽出）
docker compose exec polibase uv run python -m src.main2  # 政治家抽出（発言者抽出）
docker compose exec polibase uv run python update_speaker_links_llm.py  # LLM発言者マッチング
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
