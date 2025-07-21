#!/bin/bash

# Setup git hooks for the project
# This configures git to use the project's .githooks directory

echo "Setting up git hooks..."

# Configure git to use the project's hooks directory
git config core.hooksPath .githooks

echo "✅ Git hooks configured successfully!"
echo "   Hooks directory: .githooks/"
echo ""
echo "To apply this configuration to the main repository and all worktrees:"
echo "  1. Go to your main repository"
echo "  2. Run: git config core.hooksPath .githooks"
echo ""
echo "This only needs to be done once per clone."
