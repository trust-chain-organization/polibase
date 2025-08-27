# justfile with git worktree support

# Setup worktree ports if needed (only runs in worktree)
_setup_worktree:
	#!/bin/bash
	if [ ! -f docker/docker-compose.override.yml ]; then
		if [ "$(git rev-parse --git-common-dir 2>/dev/null)" != ".git" ]; then
			echo "Git worktree detected. Setting up port configuration..."
			./scripts/setup-worktree-ports.sh
		fi
	fi

# Get compose command based on override file existence
compose_cmd := `if [ -f docker/docker-compose.override.yml ]; then echo "-f docker/docker-compose.yml -f docker/docker-compose.override.yml"; else echo "-f docker/docker-compose.yml"; fi`

default: format

# Stop and remove containers
down: _setup_worktree
	docker compose {{compose_cmd}} down --remove-orphans

# Start containers and launch Streamlit
up: _setup_worktree
	docker compose {{compose_cmd}} up -d
	docker compose {{compose_cmd}} exec polibase uv run polibase streamlit

# Connect to database
db: _setup_worktree
	docker compose {{compose_cmd}} exec postgres psql -U polibase_user -d polibase_db

# Run tests with type checking
test: _setup_worktree
	uv run --frozen pyright
	docker compose {{compose_cmd}} up -d
	docker compose {{compose_cmd}} exec polibase uv run pytest

# Format code
format:
	uv run --frozen ruff format .

# Lint code
lint:
	uv run --frozen ruff check . --fix

# Run pytest only
pytest: _setup_worktree
	docker compose {{compose_cmd}} exec polibase uv run pytest

# Run monitoring dashboard
monitoring: _setup_worktree
	docker compose {{compose_cmd}} exec polibase uv run polibase monitoring

# Process meeting minutes
process-minutes: _setup_worktree
	docker compose {{compose_cmd}} exec polibase uv run polibase process-minutes

# Show all available CLI commands
help: _setup_worktree
	docker compose {{compose_cmd}} exec polibase uv run polibase --help

# Rebuild containers
rebuild: _setup_worktree
	docker compose {{compose_cmd}} build --no-cache

# View logs
logs: _setup_worktree
	docker compose {{compose_cmd}} logs -f

# Execute arbitrary command in container
exec *args: _setup_worktree
	docker compose {{compose_cmd}} exec polibase {{args}}

# Clean up all containers and volumes (dangerous!)
clean: down
	docker compose -f docker/docker-compose.yml down -v
	docker compose -f docker/docker-compose.yml rm -f

# Show current port configuration
ports:
	#!/bin/bash
	if [ -f docker/docker-compose.override.yml ]; then
		echo "Current port configuration (from override):"
		grep -A1 "ports:" docker/docker-compose.override.yml | grep -E "[0-9]+:" | sed 's/.*- "/  /' | sed 's/"//'
	else
		echo "Using default port configuration"
	fi
