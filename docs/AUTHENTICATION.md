# 認証設定ガイド

このドキュメントでは、Polibase Streamlitアプリケーションの Google OAuth 2.0 認証機能の設定方法について説明します。

## 概要

Polibaseは、Google OAuth 2.0を使用したユーザー認証をサポートしています。この機能により、許可されたGoogleアカウントのみがアプリケーションにアクセスできるようになります。

### 主な機能

- **Google OAuth 2.0認証**: Googleアカウントでのログイン
- **ホワイトリスト方式**: 許可されたメールアドレスのみアクセス可能
- **セッション管理**: ログイン状態の維持
- **ログアウト機能**: 安全なログアウト処理
- **開発モード**: 認証を無効化した開発環境のサポート

## Google Cloud Console での設定

### 1. プロジェクトの作成

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成するか、既存のプロジェクトを選択

### 2. OAuth 2.0 クライアントIDの作成

1. 左側メニューから「APIとサービス」→「認証情報」を選択
2. 「認証情報を作成」→「OAuth クライアント ID」をクリック
3. アプリケーションの種類: **ウェブアプリケーション**を選択
4. 名前: 任意の名前を入力（例: Polibase Streamlit App）
5. 承認済みのリダイレクト URI を追加:
   - 開発環境: `http://localhost:8501/`
   - 本番環境: `https://your-domain.com/`
6. 「作成」をクリック
7. **クライアントID**と**クライアントシークレット**をメモ

### 3. OAuth同意画面の設定

1. 「APIとサービス」→「OAuth同意画面」を選択
2. ユーザータイプを選択（内部または外部）
3. アプリケーション情報を入力:
   - アプリ名: Polibase
   - サポートメール: あなたのメールアドレス
   - デベロッパーの連絡先情報: あなたのメールアドレス
4. スコープの設定（以下を追加）:
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
   - `openid`
5. 保存して次へ

## 環境変数の設定

### 必須の環境変数

`.env`ファイルに以下の環境変数を追加します（`.env.example`を参考にしてください）:

```bash
# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8501/
```

### オプションの環境変数

```bash
# ホワイトリスト（カンマ区切りで複数指定可能）
GOOGLE_OAUTH_ALLOWED_EMAILS=user1@example.com,user2@example.com

# 開発モード（認証を無効化）
GOOGLE_OAUTH_DISABLED=false
```

## ホワイトリストの設定

### すべてのGoogleアカウントを許可

`GOOGLE_OAUTH_ALLOWED_EMAILS`を空のままにするか、環境変数を設定しない:

```bash
GOOGLE_OAUTH_ALLOWED_EMAILS=
```

### 特定のメールアドレスのみ許可

カンマ区切りでメールアドレスを指定:

```bash
GOOGLE_OAUTH_ALLOWED_EMAILS=admin@example.com,user@example.com,another@example.com
```

### ドメイン全体を許可

現在、ドメイン全体の許可はサポートされていません。個別のメールアドレスを指定してください。

## 開発環境での使用

### 認証を無効化（開発モード）

開発環境で認証をスキップしたい場合:

```bash
GOOGLE_OAUTH_DISABLED=true
```

**警告**: 本番環境では必ず`false`に設定してください。

### Dockerコンテナでの実行

Dockerコンテナ内で実行する場合、リダイレクトURIを適切に設定:

```bash
# docker-compose.yml または .env
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8501/
```

## 本番環境への デプロイ

### 1. 環境変数の設定

本番環境では、以下の方法で環境変数を設定:

- **Cloud Run**: Secret Managerを使用
- **Kubernetes**: Secretsを使用
- **その他**: 環境変数または設定ファイルで設定

### 2. リダイレクトURIの更新

本番環境のドメインに合わせてリダイレクトURIを更新:

```bash
GOOGLE_OAUTH_REDIRECT_URI=https://your-domain.com/
```

Google Cloud Consoleの「承認済みのリダイレクト URI」にも追加してください。

### 3. ホワイトリストの設定

本番環境では必ずホワイトリストを設定:

```bash
GOOGLE_OAUTH_ALLOWED_EMAILS=admin@company.com,user1@company.com
```

### 4. 認証の有効化

本番環境では認証を必ず有効化:

```bash
GOOGLE_OAUTH_DISABLED=false
```

## トラブルシューティング

### エラー: "認証設定エラー"

**原因**: 環境変数が正しく設定されていない

**解決策**:
- `.env`ファイルに`GOOGLE_OAUTH_CLIENT_ID`と`GOOGLE_OAUTH_CLIENT_SECRET`が設定されているか確認
- 値が正しくコピーされているか確認（余分なスペースがないか）

### エラー: "アクセスが拒否されました"

**原因**: ユーザーのメールアドレスがホワイトリストに含まれていない

**解決策**:
- `GOOGLE_OAUTH_ALLOWED_EMAILS`にユーザーのメールアドレスを追加
- または、ホワイトリストを無効化（空に設定）

### エラー: "redirect_uri_mismatch"

**原因**: リダイレクトURIがGoogle Cloud Consoleの設定と一致していない

**解決策**:
1. Google Cloud Consoleで設定したリダイレクトURIを確認
2. `.env`ファイルの`GOOGLE_OAUTH_REDIRECT_URI`を修正
3. 末尾のスラッシュ（`/`）を確認（あり/なしで異なる）

### ログインボタンが表示されない

**原因**: 認証が無効化されているか、設定エラー

**解決策**:
- `GOOGLE_OAUTH_DISABLED=false`を確認
- ブラウザのコンソールでエラーを確認
- Streamlitアプリを再起動

## セキュリティのベストプラクティス

### 1. 環境変数の管理

- `.env`ファイルをGitにコミットしない（`.gitignore`に追加済み）
- 本番環境ではSecret Managerなどの安全な方法で管理

### 2. ホワイトリストの使用

- 本番環境では必ずホワイトリストを設定
- 定期的にアクセス権限を見直す

### 3. HTTPS の使用

- 本番環境では必ずHTTPSを使用
- HTTPSでない場合、認証情報が漏洩するリスクがある

### 4. トークンの有効期限

- アクセストークンには有効期限がある
- 期限切れ時は自動的にログアウトされる

## 使用方法

### ログイン

1. アプリケーションにアクセス
2. "Googleでログイン"ボタンをクリック
3. Googleアカウントを選択して認証
4. 許可されたアカウントの場合、アプリケーションにアクセス可能

### ログアウト

1. サイドバーのユーザー情報を確認
2. "ログアウト"ボタンをクリック
3. セッションがクリアされ、ログインページにリダイレクト

## 参考リンク

- [Google OAuth 2.0 ドキュメント](https://developers.google.com/identity/protocols/oauth2)
- [Streamlit OAuth ライブラリ](https://github.com/dnplus/streamlit-oauth)
- [Google Cloud Console](https://console.cloud.google.com/)

## サポート

問題が解決しない場合は、以下を確認してください:

1. 環境変数が正しく設定されているか
2. Google Cloud Consoleの設定が正しいか
3. アプリケーションのログにエラーメッセージがないか

それでも解決しない場合は、開発チームにお問い合わせください。
