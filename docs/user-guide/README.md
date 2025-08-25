# Polibase ユーザーガイド

## 目次
- [システム概要](#システム概要)
- [基本的な使い方](#基本的な使い方)
- [CLIコマンドリファレンス](#cliコマンドリファレンス)
- [Streamlit UI操作ガイド](#streamlit-ui操作ガイド)
- [ワークフロー例](#ワークフロー例)

## システム概要

Polibaseは、日本の政治活動を追跡・分析するためのシステムです。以下の機能を提供します：

- 議事録の自動処理と発言抽出
- 政治家情報の収集と管理
- 発言者と政治家のマッチング
- 会議体メンバーの管理
- データの可視化とモニタリング

## 基本的な使い方

### 初期セットアップ

```bash
# 1. 環境変数設定
cp .env.example .env
# .envファイルを編集してGOOGLE_API_KEYを設定

# 2. Docker環境起動
docker compose -f docker/docker-compose.yml up -d

# 3. データベース初期化
./test-setup.sh

# 4. 動作確認
docker compose exec polibase uv run polibase --help
```

## CLIコマンドリファレンス

### 基本コマンド構文

```bash
docker compose exec polibase uv run polibase [コマンド] [オプション]
```

### 主要コマンド一覧

#### process-minutes - 議事録処理

議事録PDFやテキストから発言を抽出します。

```bash
# 会議IDを指定して処理
polibase process-minutes --meeting-id 123

# 強制的に再処理
polibase process-minutes --meeting-id 123 --force

# GCSから取得して処理
polibase process-minutes --meeting-id 123 --from-gcs
```

**オプション:**
- `--meeting-id`: 処理する会議のID（必須）
- `--force`: 既存データを上書き
- `--from-gcs`: GCSからデータを取得

#### scrape-politicians - 政治家情報収集

政党ウェブサイトから政治家情報を収集します。

```bash
# 全政党の情報を収集
polibase scrape-politicians --all-parties

# 特定政党のみ
polibase scrape-politicians --party-id 5

# ドライラン（実行せずに確認）
polibase scrape-politicians --all-parties --dry-run
```

**オプション:**
- `--all-parties`: すべての政党を処理
- `--party-id`: 特定の政党IDを指定
- `--dry-run`: 実行せずに処理内容を確認

#### update-speakers - スピーカーマッチング

発言者と政治家をマッチングします。

```bash
# LLMを使用してマッチング
polibase update-speakers --use-llm

# 処理数を制限
polibase update-speakers --use-llm --limit 100

# 信頼度閾値を設定
polibase update-speakers --use-llm --confidence 0.8
```

#### extract-conference-members - 会議メンバー抽出

会議体のメンバー情報を抽出します（3段階プロセス）。

```bash
# Step 1: メンバー抽出
polibase extract-conference-members --conference-id 185

# Step 2: 政治家とマッチング
polibase match-conference-members --conference-id 185

# Step 3: 所属情報作成
polibase create-affiliations --conference-id 185
```

#### scrape-minutes - 議事録スクレイピング

ウェブサイトから議事録を取得します。

```bash
# 単一URLから取得
polibase scrape-minutes "https://example.com/minutes.html"

# GCSにアップロード
polibase scrape-minutes "URL" --upload-to-gcs

# バッチ処理
polibase batch-scrape --tenant kyoto --upload-to-gcs
```

#### database - データベース管理

データベースのバックアップとリストアを行います。

```bash
# バックアップ作成
polibase database backup

# ローカルのみバックアップ
polibase database backup --no-gcs

# リストア
polibase database restore backup.sql

# GCSからリストア
polibase database restore gs://bucket/backup.sql

# バックアップ一覧表示
polibase database list
```

#### streamlit - Web UI起動

StreamlitのWeb UIを起動します。

```bash
# Web UI起動
polibase streamlit

# ポート指定
polibase streamlit --port 8502
```

#### monitoring - モニタリングダッシュボード

データカバレッジのモニタリングダッシュボードを起動します。

```bash
# モニタリング起動
polibase monitoring
```

## Streamlit UI操作ガイド

### アクセス方法

```
http://localhost:8501
```

### 画面構成

#### 会議管理
会議の一覧表示と詳細情報の管理を行います。

**機能:**
- 会議一覧の表示
- 会議詳細の閲覧
- 議事録URLの登録
- 処理ステータスの確認

**操作手順:**
1. サイドバーから「会議管理」を選択
2. 会議体でフィルタリング
3. 会議を選択して詳細表示
4. 「議事録処理」ボタンで処理開始

#### 政党管理
政党情報とメンバーリストURLの管理を行います。

**機能:**
- 政党一覧の表示
- メンバーリストURLの登録
- スクレイピング実行

**操作手順:**
1. サイドバーから「政党管理」を選択
2. 政党を選択
3. メンバーリストURLを入力
4. 「保存」ボタンでURL登録

#### 会議体管理
会議体（議会・委員会）の管理を行います。

**機能:**
- 会議体一覧の表示
- メンバー紹介URLの登録
- 議員団情報の管理

**操作手順:**
1. サイドバーから「会議体管理」を選択
2. 開催主体でフィルタリング
3. 会議体を選択
4. メンバー紹介URLを登録

#### 政治家管理
政治家情報の検索と編集を行います。

**機能:**
- 政治家検索（名前、政党、地域）
- 詳細情報の表示
- 発言履歴の確認
- 所属履歴の表示

**検索方法:**
1. サイドバーから「政治家管理」を選択
2. 検索条件を入力
3. 「検索」ボタンをクリック
4. 結果から詳細を表示

#### モニタリング
システム全体のデータカバレッジを可視化します。

**表示内容:**
- 都道府県別カバレッジ
- 日本地図上での可視化
- 処理統計
- エラーログ

## ワークフロー例

### 新規議事録の処理

```bash
# 1. 議事録URLを登録（Streamlit UI）
# 会議管理画面で議事録URLを入力

# 2. 議事録をスクレイピング
polibase scrape-minutes "URL" --upload-to-gcs

# 3. 議事録を処理
polibase process-minutes --meeting-id 123

# 4. 発言者を抽出
polibase extract-speakers

# 5. 政治家とマッチング
polibase update-speakers --use-llm
```

### 政治家情報の更新

```bash
# 1. 政党のメンバーリストURLを設定（Streamlit UI）
# 政党管理画面でURLを登録

# 2. 全政党の情報を収集
polibase scrape-politicians --all-parties

# 3. 重複チェック（自動実行）
# スクレイピング時に自動的に重複チェック
```

### 会議メンバーの管理

```bash
# 1. 会議体のメンバー紹介URLを設定（Streamlit UI）
# 会議体管理画面でURLを登録

# 2. メンバー情報を抽出
polibase extract-conference-members --conference-id 185

# 3. 抽出結果を確認（Streamlit UI）
# ステージングテーブルで確認

# 4. 政治家とマッチング
polibase match-conference-members --conference-id 185

# 5. マッチング結果を確認
# confidence_scoreを確認し、必要に応じて手動修正

# 6. 所属情報を作成
polibase create-affiliations --conference-id 185
```

### データバックアップ

```bash
# 日次バックアップ（推奨）
polibase database backup

# リストア（必要時）
polibase database restore gs://bucket/backup_20240801.sql
```

## ベストプラクティス

### 処理順序
1. 政党情報の収集を先に実施
2. 議事録処理
3. スピーカーマッチング
4. 定期的なバックアップ

### パフォーマンス最適化
- 大量処理時は`--limit`オプションで分割
- 夜間バッチでの自動処理を推奨
- GCS使用でローカルストレージを節約

### データ品質管理
- マッチング結果の定期的な確認
- 信頼度スコアの監視
- 手動修正の記録

## トラブルシューティング

### よくある質問

**Q: 議事録処理が失敗する**
A: GOOGLE_API_KEYが正しく設定されているか確認してください。

**Q: スピーカーマッチングの精度が低い**
A: 政治家情報を最新に更新してから再実行してください。

**Q: Streamlit UIにアクセスできない**
A: Dockerコンテナが起動しているか確認してください。
```bash
docker compose ps
```

**Q: データベース接続エラー**
A: DATABASE_URLが正しく設定されているか確認してください。
```bash
docker compose exec polibase python -c "from src.config.database import test_connection; test_connection()"
```

## サポート

### ドキュメント
- [アーキテクチャ概要](../architecture/README.md)
- [開発ガイド](../guides/development.md)
- [トラブルシューティング](../troubleshooting/README.md)

### 問題報告
GitHubのIssueで報告してください：
https://github.com/trust-chain-organization/polibase/issues

### ライセンス
本システムはMITライセンスで提供されています。
