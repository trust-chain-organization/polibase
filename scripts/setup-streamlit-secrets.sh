#!/bin/bash

# Generate .streamlit/secrets.toml with dynamic port numbers based on git worktree directory
# This script should be run after setup-worktree-ports.sh

set -e

# Get the current directory
CURRENT_DIR=$(pwd)

# Get the git worktree directory name (last part of path)
WORKTREE_NAME=$(basename "$CURRENT_DIR")

# Function to calculate port offset from worktree name (same as setup-worktree-ports.sh)
calculate_port_offset() {
    local name="$1"
    local hash=0
    for (( i=0; i<${#name}; i++ )); do
        char_code=$(printf '%d' "'${name:$i:1}")
        hash=$(( (hash + char_code) % 100 ))
    done
    echo $(( hash * 10 ))
}

# Calculate offset for this worktree
OFFSET=$(calculate_port_offset "$WORKTREE_NAME")

# Define base port
BASE_STREAMLIT_PORT=8501

# Calculate actual port
STREAMLIT_PORT=$(( BASE_STREAMLIT_PORT + OFFSET ))

# Create .streamlit directory if it doesn't exist
mkdir -p .streamlit

# Check if secrets.toml already exists
if [ -f .streamlit/secrets.toml ]; then
    echo "⚠️  .streamlit/secrets.toml already exists."
    echo "   Updating redirect_uri to use port $STREAMLIT_PORT..."

    # Update redirect_uri in existing file
    if [ "$(uname)" = "Darwin" ]; then
        # macOS
        sed -i '' "s|redirect_uri = \"http://localhost:[0-9]\+/oauth2callback\"|redirect_uri = \"http://localhost:$STREAMLIT_PORT/oauth2callback\"|" .streamlit/secrets.toml
    else
        # Linux
        sed -i "s|redirect_uri = \"http://localhost:[0-9]\+/oauth2callback\"|redirect_uri = \"http://localhost:$STREAMLIT_PORT/oauth2callback\"|" .streamlit/secrets.toml
    fi

    echo "✅ Updated redirect_uri in .streamlit/secrets.toml"
    echo "   Using port: $STREAMLIT_PORT"
else
    echo "📝 Creating .streamlit/secrets.toml for worktree: $WORKTREE_NAME"

    # Create secrets.toml with dynamic port
    cat > .streamlit/secrets.toml << EOF
# Streamlit認証設定
# このファイルは .gitignore に含まれています（機密情報を含むため）
# このファイルは scripts/setup-streamlit-secrets.sh により自動生成されました

[auth]
# OAuth 2.0 リダイレクトURI（worktree固有のポート: $STREAMLIT_PORT）
redirect_uri = "http://localhost:$STREAMLIT_PORT/oauth2callback"

# Cookieの署名に使用するシークレット
# 生成方法: python -c "import secrets; print(secrets.token_urlsafe(32))"
cookie_secret = "${STREAMLIT_COOKIE_SECRET:-REPLACE_WITH_YOUR_RANDOM_SECRET}"

# Google OAuth 2.0 クライアントID
client_id = "${GOOGLE_OAUTH_CLIENT_ID:-YOUR_CLIENT_ID.apps.googleusercontent.com}"

# Google OAuth 2.0 クライアントシークレット
client_secret = "${GOOGLE_OAUTH_CLIENT_SECRET:-YOUR_CLIENT_SECRET}"

# Google OpenID Connect メタデータURL（変更不要）
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
EOF

    echo "✅ Created .streamlit/secrets.toml"
    echo "   Port: $STREAMLIT_PORT"
    echo "   Redirect URI: http://localhost:$STREAMLIT_PORT/oauth2callback"
    echo ""
    echo "⚠️  Next steps:"
    echo "   1. Set environment variables in .env:"
    echo "      STREAMLIT_COOKIE_SECRET=<random_secret>"
    echo "      GOOGLE_OAUTH_CLIENT_ID=<your_client_id>"
    echo "      GOOGLE_OAUTH_CLIENT_SECRET=<your_client_secret>"
    echo "   2. Or manually edit .streamlit/secrets.toml"
    echo "   3. Add this redirect URI to Google Cloud Console:"
    echo "      http://localhost:$STREAMLIT_PORT/oauth2callback"
fi

echo ""
echo "📌 Don't forget to add the following URIs to Google Cloud Console:"
echo "   OAuth 2.0 Client ID → Authorized redirect URIs:"
echo "   - http://localhost:$STREAMLIT_PORT/oauth2callback"
echo ""
echo "💡 Tip: Register multiple ports (8501-8600) in Google Cloud Console"
echo "   to avoid reconfiguration for each worktree."
