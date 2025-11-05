#!/bin/bash
# Cloud SQL Proxy セットアップスクリプト
# このスクリプトはCloud SQL Proxyをダウンロード、インストール、起動します

set -e

# 設定
PROXY_VERSION="v2.8.0"  # Cloud SQL Auth Proxy version
PROXY_DIR="$HOME/.cloud-sql-proxy"
PROXY_BINARY="$PROXY_DIR/cloud-sql-proxy"

# カラー出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🔧 Cloud SQL Proxy セットアップ"
echo "================================"
echo ""

# OS検出
OS="$(uname -s)"
case "${OS}" in
    Linux*)     PLATFORM=linux;;
    Darwin*)    PLATFORM=darwin;;
    *)
        echo -e "${RED}❌ サポートされていないOS: ${OS}${NC}"
        exit 1
        ;;
esac

# アーキテクチャ検出
ARCH="$(uname -m)"
case "${ARCH}" in
    x86_64)     ARCH=amd64;;
    aarch64|arm64)  ARCH=arm64;;
    *)
        echo -e "${RED}❌ サポートされていないアーキテクチャ: ${ARCH}${NC}"
        exit 1
        ;;
esac

DOWNLOAD_URL="https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/${PROXY_VERSION}/cloud-sql-proxy.${PLATFORM}.${ARCH}"

# 1. 既存インストールの確認
echo "🔍 既存のCloud SQL Proxyを確認中..."

if command -v cloud-sql-proxy &> /dev/null; then
    INSTALLED_VERSION=$(cloud-sql-proxy --version 2>&1 | head -n 1 || echo "unknown")
    echo -e "${GREEN}✅ Cloud SQL Proxyがシステムにインストールされています${NC}"
    echo "   バージョン: $INSTALLED_VERSION"
    PROXY_BINARY="cloud-sql-proxy"
elif [ -f "$PROXY_BINARY" ]; then
    INSTALLED_VERSION=$($PROXY_BINARY --version 2>&1 | head -n 1 || echo "unknown")
    echo -e "${GREEN}✅ Cloud SQL Proxyが $PROXY_DIR にあります${NC}"
    echo "   バージョン: $INSTALLED_VERSION"
else
    echo -e "${YELLOW}⚠️  Cloud SQL Proxyが見つかりません。インストールします...${NC}"

    # ディレクトリ作成
    mkdir -p "$PROXY_DIR"

    # ダウンロード
    echo "📥 Cloud SQL Proxyをダウンロード中..."
    echo "   URL: $DOWNLOAD_URL"

    if command -v curl &> /dev/null; then
        curl -o "$PROXY_BINARY" "$DOWNLOAD_URL"
    elif command -v wget &> /dev/null; then
        wget -O "$PROXY_BINARY" "$DOWNLOAD_URL"
    else
        echo -e "${RED}❌ curlまたはwgetが必要です${NC}"
        exit 1
    fi

    # 実行権限付与
    chmod +x "$PROXY_BINARY"

    echo -e "${GREEN}✅ Cloud SQL Proxyをインストールしました: $PROXY_BINARY${NC}"

    # PATHに追加（オプション）
    echo ""
    echo -e "${YELLOW}💡 PATHに追加するには、以下を ~/.bashrc または ~/.zshrc に追加してください:${NC}"
    echo "   export PATH=\"\$PATH:$PROXY_DIR\""
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 2. 環境変数の確認
echo "🔧 環境設定を確認中..."

# .envファイルを読み込む
if [ -f .env ]; then
    source .env
else
    echo -e "${YELLOW}⚠️  .envファイルが見つかりません${NC}"
fi

CONNECTION_NAME="${CLOUD_SQL_CONNECTION_NAME:-}"
UNIX_SOCKET_DIR="${CLOUD_SQL_UNIX_SOCKET_DIR:-/cloudsql}"

if [ -z "$CONNECTION_NAME" ]; then
    echo -e "${YELLOW}⚠️  CLOUD_SQL_CONNECTION_NAMEが設定されていません${NC}"
    echo ""
    echo "以下の手順で設定してください:"
    echo ""
    echo "1. .envファイルに以下を追加:"
    echo "   CLOUD_SQL_CONNECTION_NAME=PROJECT_ID:REGION:INSTANCE_NAME"
    echo "   USE_CLOUD_SQL_PROXY=true"
    echo ""
    echo "2. 接続名を確認するには:"
    echo "   gcloud sql instances describe INSTANCE_NAME --format='value(connectionName)'"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ 接続名: $CONNECTION_NAME${NC}"
echo -e "${GREEN}✅ Unixソケットディレクトリ: $UNIX_SOCKET_DIR${NC}"

# 3. GCP認証の確認
echo ""
echo "🔑 GCP認証を確認中..."

if gcloud auth application-default print-access-token &> /dev/null; then
    echo -e "${GREEN}✅ GCP認証が設定されています${NC}"
else
    echo -e "${YELLOW}⚠️  GCP認証が設定されていません${NC}"
    echo ""
    echo "以下のコマンドで認証してください:"
    echo "   gcloud auth application-default login"
    echo ""
    read -p "今すぐ認証しますか？ (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        gcloud auth application-default login
    else
        echo -e "${RED}❌ 認証なしではCloud SQL Proxyを起動できません${NC}"
        exit 1
    fi
fi

# 4. Unixソケットディレクトリの作成
echo ""
echo "📁 Unixソケットディレクトリを準備中..."

if [ ! -d "$UNIX_SOCKET_DIR" ]; then
    echo -e "${YELLOW}⚠️  $UNIX_SOCKET_DIR が存在しません。作成します...${NC}"

    # sudoが必要かチェック
    if [ -w "$(dirname "$UNIX_SOCKET_DIR")" ]; then
        mkdir -p "$UNIX_SOCKET_DIR"
    else
        sudo mkdir -p "$UNIX_SOCKET_DIR"
        sudo chmod 777 "$UNIX_SOCKET_DIR"
    fi
fi

if [ -w "$UNIX_SOCKET_DIR" ]; then
    echo -e "${GREEN}✅ $UNIX_SOCKET_DIR は書き込み可能です${NC}"
else
    echo -e "${RED}❌ $UNIX_SOCKET_DIR に書き込み権限がありません${NC}"
    echo "   以下のコマンドで権限を変更してください:"
    echo "   sudo chmod 777 $UNIX_SOCKET_DIR"
    exit 1
fi

# 5. Cloud SQL Proxyの起動
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Cloud SQL Proxyを起動しますか？"
echo ""
echo "起動コマンド:"
echo "   $PROXY_BINARY --unix-socket=$UNIX_SOCKET_DIR $CONNECTION_NAME"
echo ""
read -p "起動しますか？ (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${GREEN}🚀 Cloud SQL Proxyを起動中...${NC}"
    echo ""

    # バックグラウンドで起動
    nohup "$PROXY_BINARY" --unix-socket="$UNIX_SOCKET_DIR" "$CONNECTION_NAME" > /tmp/cloud-sql-proxy.log 2>&1 &
    PROXY_PID=$!

    echo -e "${GREEN}✅ Cloud SQL Proxyが起動しました (PID: $PROXY_PID)${NC}"
    echo "   ログファイル: /tmp/cloud-sql-proxy.log"
    echo ""

    # 起動確認
    sleep 3
    if ps -p $PROXY_PID > /dev/null; then
        echo -e "${GREEN}✅ Cloud SQL Proxyは正常に動作しています${NC}"
        echo ""
        echo "接続確認:"
        echo "   tail -f /tmp/cloud-sql-proxy.log"
    else
        echo -e "${RED}❌ Cloud SQL Proxyの起動に失敗しました${NC}"
        echo "   ログを確認してください: cat /tmp/cloud-sql-proxy.log"
        exit 1
    fi
else
    echo ""
    echo -e "${YELLOW}💡 後で手動で起動する場合:${NC}"
    echo "   $PROXY_BINARY --unix-socket=$UNIX_SOCKET_DIR $CONNECTION_NAME"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✨ セットアップ完了！"
echo ""
echo "📝 次のステップ:"
echo "   1. .envファイルで USE_CLOUD_SQL_PROXY=true を設定"
echo "   2. アプリケーションを起動: just streamlit"
echo "   3. データベース接続を確認: python -m src.infrastructure.config.database"
echo ""
echo "🛑 Cloud SQL Proxyを停止するには:"
echo "   pkill cloud-sql-proxy"
echo ""
