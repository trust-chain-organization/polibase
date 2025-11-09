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

デプロイ方法については、以下のプラットフォームをご検討ください：

- **GitHub Pages**: 無料、簡単に設定可能
- **Netlify**: 継続的デプロイ、プレビュー機能
- **Vercel**: 高速、簡単なデプロイ
- **Cloudflare Pages**: グローバルCDN、無料

デプロイ設定の詳細は、別途ドキュメントを参照してください。

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
