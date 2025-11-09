# Task Completion Checklist

When completing a task in Polibase, ALWAYS perform these checks:

## 1. Code Quality Checks (REQUIRED)
```bash
# Format code with Ruff
docker compose -f docker/docker-compose.yml exec sagebase uv run --frozen ruff format .

# Check linting with Ruff
docker compose -f docker/docker-compose.yml exec sagebase uv run --frozen ruff check .
docker compose -f docker/docker-compose.yml exec sagebase uv run --frozen ruff check . --fix  # Auto-fix issues

# Type checking with Pyright
# NOTE: Run locally, not in Docker
uv run --frozen pyright
```

## 2. Run Tests
```bash
# Run all tests
docker compose -f docker/docker-compose.yml exec sagebase uv run pytest

# Run specific test file
docker compose -f docker/docker-compose.yml exec sagebase uv run pytest tests/test_specific.py -v
```

## 3. Verify Functionality
- If modifying minutes processing: Run `polibase process-minutes`
- If modifying UI: Test with `polibase streamlit`
- If modifying scraping: Test specific scraper commands
- Always verify database changes are applied correctly

## 4. Database Migrations
When adding new migration files:
1. Create in `database/migrations/` with sequential numbering (e.g., `016_*.sql`)
2. **MUST** add to `database/02_run_migrations.sql` for reset-database.sh
3. Test migration:
```bash
docker compose -f docker/docker-compose.yml exec sagebase cat /app/database/migrations/016_new_migration.sql | docker compose -f docker/docker-compose.yml exec -T postgres psql -U sagebase_user -d sagebase_db
```

## 5. Pre-commit Hooks
```bash
# Run pre-commit on changed files
docker compose -f docker/docker-compose.yml exec sagebase uv run pre-commit run

# Run on all files
docker compose -f docker/docker-compose.yml exec sagebase uv run pre-commit run --all-files
```

## 6. UI Testing (if UI changes)
Use Playwright MCP tools to:
- Navigate to Streamlit (check port with `docker ps`)
- Take screenshots to verify changes
- Test functionality
- Capture any error messages

## 7. Update Documentation
- Update CLAUDE.md if adding new patterns or commands
- Document in tmp/ directory for planning/intermediate files
- Never create documentation unless explicitly requested

## Important Notes
- NEVER commit unless explicitly asked
- If lint/typecheck commands are missing, ask user and suggest adding to CLAUDE.md
- Create temporary files only in tmp/ directory
