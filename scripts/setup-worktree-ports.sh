#!/bin/bash

# Generate docker-compose.override.yml with dynamic port numbers based on git worktree directory
# This prevents port conflicts when running multiple Docker instances across different worktrees

set -e

# Get the current directory
CURRENT_DIR=$(pwd)

# Get the git worktree directory name (last part of path)
WORKTREE_NAME=$(basename "$CURRENT_DIR")

# Function to calculate port offset from worktree name
calculate_port_offset() {
    local name="$1"
    # Use hash of the directory name to generate a stable offset
    # We use sum of character codes modulo 100 to get a number between 0-99
    local hash=0
    for (( i=0; i<${#name}; i++ )); do
        char_code=$(printf '%d' "'${name:$i:1}")
        hash=$(( (hash + char_code) % 100 ))
    done
    # Multiply by 10 to get reasonable spacing between instances (0, 10, 20, ..., 990)
    echo $(( hash * 10 ))
}

# Calculate offset for this worktree
OFFSET=$(calculate_port_offset "$WORKTREE_NAME")

# Define base ports
BASE_POLIBASE_PORT=8000
BASE_STREAMLIT_PORT=8501
BASE_MONITORING_PORT=8502
BASE_POSTGRES_PORT=5432

# Calculate actual ports
POLIBASE_PORT=$(( BASE_POLIBASE_PORT + OFFSET ))
STREAMLIT_PORT=$(( BASE_STREAMLIT_PORT + OFFSET ))
MONITORING_PORT=$(( BASE_MONITORING_PORT + OFFSET ))
POSTGRES_PORT=$(( BASE_POSTGRES_PORT + OFFSET ))

# Create docker-compose.override.yml
cat > docker/docker-compose.override.yml << EOF
# Auto-generated for worktree: $WORKTREE_NAME
# This file overrides port configurations to prevent conflicts
# DO NOT COMMIT THIS FILE

services:
  polibase:
    ports: !override
      - "$POLIBASE_PORT:8000"
      - "$STREAMLIT_PORT:8501"

  polibase-monitoring:
    ports: !override
      - "$MONITORING_PORT:8502"

  postgres:
    ports: !override
      - "$POSTGRES_PORT:5432"
EOF

echo "✅ Created docker-compose.override.yml for worktree: $WORKTREE_NAME"
echo "   Port configuration:"
echo "     - Polibase API: $POLIBASE_PORT"
echo "     - Streamlit UI: $STREAMLIT_PORT"
echo "     - Monitoring: $MONITORING_PORT"
echo "     - PostgreSQL: $POSTGRES_PORT"
echo "   Port offset: $OFFSET"
echo ""
echo "You can now use standard Docker commands:"
echo "  docker compose -f docker/docker-compose.yml up -d"
