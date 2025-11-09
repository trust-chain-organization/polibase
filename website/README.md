# Polibase Website

Polibase（政治活動追跡アプリケーション）の公式ウェブサイトです。

## 概要

このサイトは、Hugoフレームワークを使用して構築された静的サイトで、Polibaseの機能や使い方を紹介しています。

## 技術スタック

- **フレームワーク**: Hugo v0.152.2+extended
- **テーマ**: [PaperMod](https://github.com/adityatelange/hugo-PaperMod)
- **言語**: 日本語

## セットアップ手順

### 1. Hugoのインストール

#### macOS
```bash
brew install hugo
```

#### Linux
```bash
# Snapを使用する場合
snap install hugo

# または、公式バイナリをダウンロード
wget https://github.com/gohugoio/hugo/releases/download/v0.152.2/hugo_extended_0.152.2_linux-amd64.tar.gz
tar -xzf hugo_extended_0.152.2_linux-amd64.tar.gz
sudo mv hugo /usr/local/bin/
```

#### Windows
```powershell
# Chocolateyを使用する場合
choco install hugo-extended

# または、Scoopを使用する場合
scoop install hugo-extended
```

### 2. リポジトリのクローン

```bash
git clone https://github.com/trust-chain-organization/polibase.git
cd sagebase/website
```

### 3. サブモジュールの初期化

PaperModテーマはGitサブモジュールとして管理されています。

```bash
git submodule update --init --recursive
```

### 4. ローカルでの開発サーバー起動

```bash
hugo server --buildDrafts
```

ブラウザで http://localhost:1313 にアクセスすると、サイトを確認できます。

## プロジェクト構造

```
website/
├── archetypes/       # コンテンツのテンプレート
├── content/          # ページコンテンツ（Markdownファイル）
│   ├── about.md      # 概要ページ
│   ├── features.md   # 機能紹介ページ
│   └── contact.md    # お問い合わせページ
├── data/             # データファイル
├── layouts/          # カスタムレイアウト
├── static/           # 静的ファイル（画像、CSS、JSなど）
├── themes/           # テーマディレクトリ
│   └── PaperMod/     # PaperModテーマ（サブモジュール）
└── hugo.toml         # サイト設定ファイル
```

## コンテンツの追加

新しいページを作成するには：

```bash
hugo new content/<ページ名>.md
```

例：
```bash
hugo new content/blog/my-first-post.md
```

## ビルド

本番環境用にサイトをビルドするには：

```bash
hugo --minify
```

生成されたファイルは `public/` ディレクトリに出力されます。

## デプロイ

このサイトは **Cloudflare Pages** にデプロイされます。

### 自動デプロイ

GitHubリポジトリとCloudflare Pagesが連携しており、以下のように自動デプロイされます：

- **本番環境**: `main` ブランチへのプッシュで自動デプロイ
  - URL: `<プロジェクト名>.pages.dev`
- **プレビュー環境**: その他のブランチへのプッシュでプレビュー環境が自動作成
  - URL: `<ブランチ名>.<プロジェクト名>.pages.dev`

### ビルド設定

Cloudflare Pagesでは以下の設定でビルドされます：

```
Build command: hugo --minify
Build output directory: public
Root directory: website
Environment variables:
  - HUGO_VERSION=0.152.2
  - HUGO_ENV=production
```

### 詳細な手順

Cloudflare Pagesの初回設定、カスタムドメインの設定、トラブルシューティングなど、詳細な手順については以下のドキュメントを参照してください：

📖 **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Cloudflare Pagesデプロイメント完全ガイド

## カスタマイズ

### サイト設定

`hugo.toml` ファイルを編集して、サイトの基本設定を変更できます：

- サイトタイトル
- ベースURL
- メニュー構成
- テーマパラメータ

### テーマのカスタマイズ

PaperModテーマの詳細なカスタマイズ方法は、[公式ドキュメント](https://adityatelange.github.io/hugo-PaperMod/)を参照してください。

## トラブルシューティング

### テーマが表示されない

サブモジュールが正しく初期化されているか確認してください：

```bash
git submodule update --init --recursive
```

### ビルドエラー

Hugo Extended版がインストールされているか確認してください：

```bash
hugo version
```

出力に `+extended` が含まれていることを確認します。

## ライセンス

[ライセンス情報を追加]

## お問い合わせ

ご質問やご提案は、[GitHubのIssue](https://github.com/trust-chain-organization/polibase/issues)からお願いします。
