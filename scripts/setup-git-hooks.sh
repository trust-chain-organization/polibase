#!/bin/bash
# Setup Git hooks for automatic .env file copying in worktrees

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up Git hooks...${NC}"

# Get the main repository path
MAIN_REPO_PATH=$(git worktree list --porcelain | grep "^worktree" | head -n1 | cut -d' ' -f2)

if [ -z "$MAIN_REPO_PATH" ]; then
    echo -e "${RED}Error: Could not determine main repository path${NC}"
    exit 1
fi

# Create post-checkout hook
HOOK_PATH="$MAIN_REPO_PATH/.git/hooks/post-checkout"

cat > "$HOOK_PATH" << 'EOF'
#!/bin/bash
# Post-checkout hook to copy .env file when creating a new worktree

# Check if this is a new worktree creation (coming from null commit)
if [[ "$1" == "0000000000000000000000000000000000000000" ]]; then
    # Get the main repository path dynamically
    mainRepoPath=$(git worktree list --porcelain | grep "^worktree" | head -n1 | cut -d' ' -f2)

    # Files to copy from main repository
    files=(.env)

    echo "🔧 Setting up worktree environment..."

    for file in "${files[@]}"; do
        if [ -f "$mainRepoPath/$file" ]; then
            cp "$mainRepoPath/$file" "$(pwd)/$file"
            echo "  ✅ Copied $file from main repository"
        else
            echo "  ⚠️  Warning: $file not found in main repository"
        fi
    done

    echo "🎉 Worktree setup complete!"
fi
EOF

# Make the hook executable
chmod +x "$HOOK_PATH"

echo -e "${GREEN}✅ Git hooks setup complete!${NC}"
echo -e "${YELLOW}Note: New worktrees will now automatically copy .env from the main repository${NC}"
