# Polibase Suggested Commands

## Environment Setup
```bash
# Initial setup
cp .env.example .env  # Configure GOOGLE_API_KEY
docker compose -f docker/docker-compose.yml up -d
./test-setup.sh

# Google Cloud Storage setup (optional)
gcloud auth application-default login
# Edit .env: GCS_BUCKET_NAME, GCS_UPLOAD_ENABLED=true
```

## Daily Development Commands

### Start/Stop Services
```bash
# Start services
docker compose -f docker/docker-compose.yml up -d

# Stop services (data persists)
docker compose -f docker/docker-compose.yml down

# View logs
docker compose -f docker/docker-compose.yml logs -f
```

### Main Processing Commands
```bash
# Process meeting minutes
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase process-minutes

# Extract speakers from minutes
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase extract-speakers

# Match speakers with politicians (LLM)
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase update-speakers --use-llm

# Scrape politician data from parties
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase scrape-politicians --all-parties
```

### Web UI
```bash
# Meeting management UI
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase streamlit

# Data coverage monitoring
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase monitoring
```

### Development Commands
```bash
# Format code
docker compose -f docker/docker-compose.yml exec sagebase uv run --frozen ruff format .

# Lint check
docker compose -f docker/docker-compose.yml exec sagebase uv run --frozen ruff check . --fix

# Type check (run locally)
uv run --frozen pyright

# Run tests
docker compose -f docker/docker-compose.yml exec sagebase uv run pytest

# Pre-commit hooks
docker compose -f docker/docker-compose.yml exec sagebase uv run pre-commit run --all-files
```

### Database Commands
```bash
# Connect to PostgreSQL
docker compose -f docker/docker-compose.yml exec postgres psql -U sagebase_user -d sagebase_db

# Backup database
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase database backup

# Reset database
./scripts/reset-database.sh

# Apply migration
docker compose -f docker/docker-compose.yml exec sagebase cat /app/database/migrations/XXX.sql | docker compose -f docker/docker-compose.yml exec -T postgres psql -U sagebase_user -d sagebase_db
```

### Web Scraping
```bash
# Scrape single minutes
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase scrape-minutes "URL" --upload-to-gcs

# Batch scrape
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase batch-scrape --tenant kyoto --upload-to-gcs
```

### Conference Member Extraction (3-step)
```bash
# Step 1: Extract members
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase extract-conference-members --conference-id 185

# Step 2: Match with politicians
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase match-conference-members --conference-id 185

# Step 3: Create affiliations
docker compose -f docker/docker-compose.yml exec sagebase uv run sagebase create-affiliations --conference-id 185
```

## System Commands (Darwin/macOS)
- `ls -la`: List files with details
- `cd`: Change directory
- `grep -r "pattern" .`: Recursive search
- `find . -name "*.py"`: Find files by pattern
- `git status`: Check git status
- `git diff`: View changes
- `git log --oneline -10`: Recent commits

## Port Information
When using `git worktree`, ports are auto-configured via docker-compose.override.yml. Check actual ports with:
```bash
docker ps
# or
cat docker/docker-compose.override.yml
```
