# Polibase - 政治活動追跡アプリケーション

[![Tests](https://github.com/trust-chain-organization/polibase/actions/workflows/test.yml/badge.svg)](https://github.com/trust-chain-organization/polibase/actions/workflows/test.yml)

政治家の発言、議事録、公約などを体系的に管理・分析するためのアプリケーションです。

## 🗄️ テーブル構造
詳細なデータベース設計はこちらをご確認ください：
https://dbdocs.io/polibase/Polibase

## 🚀 環境構築手順

### 前提条件
- Docker & Docker Compose
- Python 3.13
- uv（Pythonパッケージマネージャー）
- Google Cloud SDK（GCS機能を使用する場合）

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

**Google Cloud Storage（オプション）**:
- スクレイピングしたデータをGCSに保存する場合は、以下の設定も必要です：
  - `gcloud auth application-default login`で認証
  - `.env`ファイルで`GCS_BUCKET_NAME`と`GCS_UPLOAD_ENABLED=true`を設定

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

### システムデザイン

Polibaseは以下の設計原則に基づいて構築されています：

1. **政治家の情報は政党のWebサイトから取得**
   - 各政党の公式サイトから最新の議員情報を定期的に取得
   - 名前、所属、役職、選挙区などの情報を構造化して保存

2. **発言者と発言内容は議事録から抽出**
   - 議事録PDFやWebページから発言者名と発言内容を自動抽出
   - 発言順序や文脈を保持したまま構造化データとして保存

3. **発言者と政治家はLLMを利用して紐付け**
   - 表記揺れや敬称の違いに対応する高精度マッチング
   - ルールベース + LLMベースのハイブリッドアプローチ

4. **会議体の所属議員情報は段階的に抽出・マッチング**
   - 議会の議員紹介ページから情報を自動抽出
   - 中間ステージングテーブルで確認・修正が可能
   - LLMによる高精度な既存政治家とのマッチング

5. **議員団（会派）による政策の賛否を管理**
   - 議員団単位での賛成・反対を記録
   - 政治家の議員団所属履歴を管理
   - 議案への賛否を個人・政党・議員団で分析可能

6. **データ入力はStreamlit UIを通じて**
   - 政党の議員一覧URLの設定
   - 議事録URLの登録と管理
   - 会議体の議員紹介URLの設定
   - 直感的なWebインターフェースで操作

7. **データカバレッジを監視ダッシュボードで可視化**
   - 全国の議会・議事録データの入力状況を一覧表示
   - 議会別・都道府県別・政党別のカバレッジ率を視覚化
   - 時系列でのデータ入力推移を分析
   - データ充実度の低い領域を特定して効率的な作業が可能

### 統一CLIコマンド

新しく統一されたCLIインターフェースが利用可能です：

```bash
# 利用可能なコマンドを表示
docker compose exec polibase uv run polibase --help

# 議事録を処理（発言を抽出）
docker compose exec polibase uv run polibase process-minutes

# 議事録から発言者情報を抽出
docker compose exec polibase uv run polibase extract-speakers

# 発言者をマッチング（LLM使用）
docker compose exec polibase uv run polibase update-speakers --use-llm

# データベース接続をテスト
docker compose exec polibase uv run polibase test-connection

# 会議管理Web UIを起動
docker compose exec polibase uv run polibase streamlit

# データカバレッジ監視ダッシュボードを起動
docker compose exec polibase uv run polibase monitoring

# 政党議員情報を取得（Web スクレイピング）
docker compose exec polibase uv run polibase scrape-politicians --all-parties

# 会議体所属議員の抽出・マッチング（3段階処理）
# ステップ1: 議員情報を抽出
docker compose exec polibase uv run polibase extract-conference-members --conference-id 185

# ステップ2: 既存政治家とマッチング
docker compose exec polibase uv run polibase match-conference-members --conference-id 185

# ステップ3: 所属情報を作成
docker compose exec polibase uv run polibase create-affiliations --conference-id 185

# 処理状況を確認
docker compose exec polibase uv run polibase member-status
```

### アプリケーションの実行（従来の方法）

#### 議事録分割処理（発言抽出）
```bash
# Docker環境で実行（新しいファイル名でも実行可能）
docker compose exec polibase uv run python -m src.process_minutes
# または従来のコマンド
docker compose exec polibase uv run python -m src.main

# ローカル環境で実行
uv run python -m src.process_minutes

# GCSから議事録を取得して処理（meeting IDを指定）
docker compose exec polibase uv run python -m src.process_minutes --meeting-id 123
```
議事録PDFファイルを読み込み、発言単位に分割してデータベースに保存します。
meeting IDを指定すると、GCSに保存された議事録テキストを自動的に取得して処理します。

#### 発言者抽出処理
```bash
# Docker環境で実行
docker compose exec polibase uv run python -m src.extract_speakers_from_minutes

# ローカル環境で実行
uv run python -m src.extract_speakers_from_minutes
```
議事録から発言者の情報を抽出してspeakersテーブルに保存します。

#### 会議管理Web UI
```bash
# Docker環境で実行（コンテナ内で起動）
docker compose exec polibase uv run polibase streamlit --host 0.0.0.0

# Docker環境で実行（ポートフォワーディング付き）
docker compose run -p 8501:8501 polibase uv run polibase streamlit --host 0.0.0.0

# ローカル環境で実行
uv run polibase streamlit

# カスタムポートで起動
uv run polibase streamlit --port 8080
```
Webブラウザで会議情報（URL、日付）と政党情報を管理できるインターフェースを提供します：
- 会議一覧の表示・フィルタリング
- 新規会議の登録（開催主体、会議体、日付、URL）
- 既存会議の編集・削除
- 政党管理（議員一覧ページURLの設定）

#### データカバレッジ監視ダッシュボード
```bash
# Docker環境で実行（専用ポートで起動）
docker compose exec polibase uv run polibase monitoring

# カスタムポートで起動
docker compose exec polibase uv run polibase monitoring --port 8503

# Docker Composeで専用コンテナとして起動（推奨）
docker compose up -d polibase-monitoring
```
データ入力の進捗状況を可視化する監視ダッシュボードを提供します：
- **全体概要**: 議会数、会議数、議事録数、政治家数などの主要メトリクス
- **日本地図表示**: 都道府県ごとのデータ充実度を地図上で可視化
  - 議事録、議会、議員団、議会所属議員の数を色分け表示
  - インタラクティブな地図でクリック時に詳細情報を表示
  - 各種指標の切り替え表示が可能
- **議会別カバレッジ**: 各議会のデータ入力率をヒートマップで表示
- **時系列分析**: データ入力の推移を時系列グラフで確認
- **詳細分析**: 政党別、都道府県別、委員会タイプ別の充実度

アクセスURL: http://localhost:8502 （Docker Compose使用時）

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

#### 議事録Web取得処理
```bash
# 単一の議事録を取得（kaigiroku.net対応）
docker compose exec polibase uv run polibase scrape-minutes "https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=6030&schedule_id=1"

# 出力形式とディレクトリを指定
uv run polibase scrape-minutes "URL" --output-dir data/scraped --format txt

# キャッシュを無視して再取得
uv run polibase scrape-minutes "URL" --no-cache

# Google Cloud Storageにアップロード（meetingsテーブルにGCS URIを自動保存）
uv run polibase scrape-minutes "URL" --upload-to-gcs
uv run polibase scrape-minutes "URL" --upload-to-gcs --gcs-bucket my-bucket

# 複数の議事録を一括取得（kaigiroku.net）
uv run polibase batch-scrape --tenant kyoto --start-id 6000 --end-id 6100
uv run polibase batch-scrape --tenant osaka --start-id 1000 --end-id 1100

# バッチ取得でGCSにアップロード
uv run polibase batch-scrape --tenant kyoto --upload-to-gcs
```

Webサイトから議事録を自動取得し、テキストまたはJSON形式で保存します。

#### 政党議員情報取得処理（LLMベース）
```bash
# 全政党の議員情報を取得（議員一覧URLが設定されている政党）
docker compose exec polibase uv run polibase scrape-politicians --all-parties

# 特定の政党のみ取得（政党IDを指定）
docker compose exec polibase uv run polibase scrape-politicians --party-id 5

# ドライラン（データベースに保存せずに確認）
docker compose exec polibase uv run polibase scrape-politicians --all-parties --dry-run

# 最大ページ数を指定（ページネーション対応）
docker compose exec polibase uv run polibase scrape-politicians --all-parties --max-pages 5
```

各政党のWebサイトから議員情報を自動取得し、データベースに保存します。

**特徴:**
- LLMを活用してHTMLから議員情報を構造化データとして抽出
- サイト固有のセレクタに依存しない汎用的な実装
- ページネーション対応（複数ページの自動取得）
- 重複チェック機能（既存議員は更新、新規議員は追加）

**事前準備:**
1. Streamlit UIの「政党管理」タブで議員一覧ページURLを設定
2. GOOGLE_API_KEYが設定されていることを確認

**特徴:**
- JavaScriptで動的に生成される議事録にも対応
- 発言者の抽出と整理
- キャッシュ機能で再取得を効率化
- バッチ処理で複数の議事録を一括取得

**対応システム:**
- **kaigiroku.net** - 多くの地方議会で使用される統一システム
  - 京都市（tenant/kyoto）
  - 大阪市（tenant/osaka）
  - 神戸市（tenant/kobe）
  - その他多数の自治体
- 今後、独自システムを使用する自治体にも対応予定

#### 会議体所属議員の抽出・マッチング（3段階処理）

議会や委員会に所属する議員情報を段階的に抽出・マッチングする機能です。

```bash
# ステップ1: 議員情報の抽出
docker compose exec polibase uv run polibase extract-conference-members --conference-id 185
# または全会議体を処理
docker compose exec polibase uv run polibase extract-conference-members

# ステップ2: 既存政治家とのマッチング
docker compose exec polibase uv run polibase match-conference-members --conference-id 185

# ステップ3: 所属情報の作成
docker compose exec polibase uv run polibase create-affiliations --conference-id 185
docker compose exec polibase uv run polibase create-affiliations --start-date 2024-01-01

# 処理状況の確認
docker compose exec polibase uv run polibase member-status --conference-id 185
```

**処理フロー:**
1. **抽出（Extract）**: 会議体の議員紹介URLから議員名、役職、所属政党を抽出
   - Playwright + LLMでWebページを解析
   - `extracted_conference_members`テーブルに保存（ステータス: pending）

2. **マッチング（Match）**: 抽出した議員を既存の政治家データとマッチング
   - LLMによるfuzzyマッチング（表記揺れ対応）
   - 信頼度スコアを計算：
     - 0.7以上: 自動マッチング（matched）
     - 0.5-0.7: 要確認（needs_review）
     - 0.5未満: 該当なし（no_match）

3. **作成（Create）**: マッチング済みデータから正式な所属情報を作成
   - `politician_affiliations`テーブルに保存
   - 役職（議長、副議長、委員長など）も記録

**事前準備:**
1. Streamlit UIの「会議体管理」→「議員紹介URL管理」タブでURLを設定
2. 政治家マスタデータが登録されていることを確認

**特徴:**
- 各段階で処理を中断・再開可能
- 中間データを確認してから次の段階へ進める
- エラーが発生しても部分的な再処理が可能
- 信頼度に基づく柔軟なマッチング

### テストの実行
```bash
# Docker環境で実行
docker compose exec polibase uv run pytest

# ローカル環境で実行
uv run pytest

# 特定のテストを実行
uv run pytest tests/test_minutes_divider.py -v

# Streamlit関連のテストを実行
uv run pytest tests/test_streamlit_app.py tests/test_meeting_repository.py -v

# カバレッジレポート付きでテスト実行（開発時）
uv pip install pytest-cov
uv run pytest --cov=src tests/
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

Polibaseは、ローカルとGoogle Cloud Storage（GCS）の両方にデータベースバックアップを保存できます。

**GCS連携の設定（オプション）**:
- GCSを使用する場合は、事前に以下の設定が必要です：
  1. `gcloud auth application-default login`で認証
  2. `.env`ファイルで`GCS_BUCKET_NAME`と`GCS_UPLOAD_ENABLED=true`を設定
- GCSが設定されていない場合は、自動的にローカルのみのバックアップになります

#### バックアップ作成
```bash
# ローカルとGCSの両方にバックアップ（デフォルト）
docker compose exec polibase uv run polibase database backup

# ローカルのみにバックアップ
docker compose exec polibase uv run polibase database backup --no-gcs

# 従来のスクリプトを使用（ローカルのみ）
./backup-database.sh backup
```

#### バックアップ一覧の確認
```bash
# ローカルとGCSのバックアップを表示
docker compose exec polibase uv run polibase database list

# ローカルのバックアップのみ表示
docker compose exec polibase uv run polibase database list --no-gcs

# 従来のスクリプトを使用
./backup-database.sh list
```

#### リストア実行
```bash
# ローカルファイルからリストア
docker compose exec polibase uv run polibase database restore database/backups/polibase_backup_20241230_123456.sql

# GCSからリストア
docker compose exec polibase uv run polibase database restore gs://polibase-scraped-minutes/database-backups/polibase_backup_20241230_123456.sql

# 従来のスクリプトを使用（ローカルのみ）
./backup-database.sh restore database/backups/polibase_backup_20240529_123456.sql
```

#### 手動バックアップ・リストア
```bash
# 手動バックアップ
docker compose exec postgres pg_dump -U polibase_user polibase_db > backup.sql

# 手動リストア
docker compose exec -T postgres psql -U polibase_user -d polibase_db < backup.sql
```

## formattingとリンティング
`docker compose exec polibase uv sync`で依存関係をインストール
`docker compose exec polibase uv run --frozen ruff format .`でフォーマット実行
`docker compose exec polibase uv run --frozen ruff check .`でリンティング実行
`docker compose exec polibase uv run --frozen pyright`で型チェック実行
`docker compose exec polibase uv run pre-commit install`でpre-commitフックをインストール
`docker compose exec polibase uv run pre-commit run --all-files`で全ファイルチェック

## ⚙️ 環境変数設定

主要な環境変数（`.env`ファイルで設定）:

### 必須設定
- `GOOGLE_API_KEY`: Google Gemini APIキー（議事録処理・政治家抽出に必要）
- `DATABASE_URL`: PostgreSQL接続URL（デフォルト: `postgresql://polibase_user:polibase_password@localhost:5432/polibase_db`）

### タイムアウト設定（秒単位）
- `WEB_SCRAPER_TIMEOUT`: Webページ読み込みタイムアウト（デフォルト: 60秒）
- `PDF_DOWNLOAD_TIMEOUT`: PDFダウンロードタイムアウト（デフォルト: 120秒）
- `PAGE_LOAD_TIMEOUT`: ページロード状態待機タイムアウト（デフォルト: 30秒）
- `SELECTOR_WAIT_TIMEOUT`: セレクタ待機タイムアウト（デフォルト: 10秒）

### その他の設定
- `LLM_MODEL`: 使用するLLMモデル（デフォルト: `gemini-2.0-flash`）
- `LLM_TEMPERATURE`: LLMの温度パラメータ（デフォルト: 0.0）
- `GCS_BUCKET_NAME`: Google Cloud Storageバケット名
- `GCS_UPLOAD_ENABLED`: GCS自動アップロード有効化（`true`/`false`）
- `GCS_PROJECT_ID`: Google CloudプロジェクトID（省略時はデフォルト使用）

処理時間の長いスクレイピングや大きなPDFファイルの処理でタイムアウトが発生する場合は、これらの値を調整してください。

## 📁 プロジェクト構成

```
polibase/
├── src/                          # メインアプリケーションコード
│   ├── cli.py                   # 統一CLIエントリーポイント
│   ├── streamlit_app.py         # 会議管理Web UI
│   ├── process_minutes.py       # 議事録分割処理
│   ├── extract_speakers_from_minutes.py   # 発言者抽出処理
│   ├── config/                   # 設定ファイル
│   │   ├── database.py          # データベース接続設定
│   │   ├── config.py            # アプリケーション設定
│   │   └── settings.py          # 環境変数管理
│   ├── common/                   # 共通機能
│   │   ├── app_logic.py         # アプリケーション共通ロジック
│   │   └── database_utils.py    # データベース共通処理
│   ├── minutes_divide_processor/ # 議事録分割処理
│   │   └── minutes_divider.py   # 分割ロジック
│   ├── politician_extract_processor/ # 政治家抽出処理
│   ├── web_scraper/             # 議事録Web取得
│   │   ├── base_scraper.py      # スクレーパー基底クラス
│   │   ├── kaigiroku_net_scraper.py # kaigiroku.net対応スクレーパー
│   │   └── scraper_service.py   # スクレーパーサービス
│   ├── database/                 # データベースリポジトリ
│   │   ├── meeting_repository.py # 会議データリポジトリ
│   │   └── ...                  # その他リポジトリ
│   └── utils/                   # ユーティリティ関数
│       └── gcs_storage.py       # Google Cloud Storageユーティリティ（GCS URI対応）
├── database/                    # データベース関連
│   ├── init.sql                # データベース初期化スクリプト
│   ├── migrations/             # データベースマイグレーション
│   │   ├── 001_add_url_to_meetings.sql
│   │   ├── 002_add_members_list_url_to_political_parties.sql
│   │   ├── 003_add_politician_details.sql
│   │   └── 004_add_gcs_uri_to_meetings.sql  # GCS URI保存用カラム追加
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
├── CLAUDE.md                  # Claude Code用ガイド
└── polibase.dbml              # データベーススキーマ定義
```

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

### Google Cloud Storage関連の問題

#### 認証エラー
```bash
# GCP認証を再設定
gcloud auth application-default login

# プロジェクトIDを設定
gcloud config set project YOUR_PROJECT_ID
```

#### バケットアクセスエラー
```bash
# バケットの存在確認
gsutil ls gs://YOUR_BUCKET_NAME/

# 権限の確認
gsutil iam get gs://YOUR_BUCKET_NAME/
```

## 🗂️ データの流れ

### 標準フロー（PDFファイルから処理）
1. **議事録PDFの処理**: `src/process_minutes.py` - 議事録を発言単位に分割してデータベースに保存
2. **発言者情報の抽出**: `src/extract_speakers_from_minutes.py` - 発言から発言者情報を抽出してspeakersテーブルに保存
3. **発言者マッチング**: `update_speaker_links_llm.py` - LLMを活用して発言と発言者を高精度でマッチング
4. **政治家情報の取得**: `polibase scrape-politicians` - 政党のWebサイトから最新の政治家情報を取得
5. **データベース保存**: 抽出・マッチングされた情報をPostgreSQLに保存
6. **分析・検索**: 蓄積されたデータから政治活動を分析

### Webスクレイピングフロー（GCS統合）
1. **議事録Web取得**: `polibase scrape-minutes` - Webから議事録を取得
2. **GCS保存**: 取得したデータをGoogle Cloud Storageに自動アップロード
3. **URI記録**: GCS URIをmeetingsテーブルに保存
4. **GCSから処理**: `process_minutes.py --meeting-id` でGCSから直接データを取得して処理
5. **後続処理**: 政治家抽出、発言者マッチングなどの処理を実行

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

# 🏃 アプリケーション実行（新しいCLI）
docker compose exec polibase uv run polibase process-minutes      # 議事録分割
docker compose exec polibase uv run polibase extract-speakers      # 発言者抽出
docker compose exec polibase uv run polibase update-speakers --use-llm  # LLM発言者マッチング
docker compose exec polibase uv run polibase scrape-politicians --all-parties  # 政治家情報取得

# 🏃 アプリケーション実行（従来の方法）
docker compose exec polibase uv run python -m src.process_minutes  # 議事録分割（発言抽出）
docker compose exec polibase uv run python -m src.extract_speakers_from_minutes  # 発言者抽出
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
