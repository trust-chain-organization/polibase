# Polibase Codebase Structure

## Root Directory Structure
```
polibase/
├── src/                    # Main application code
├── database/              # Database scripts and migrations
├── docker/                # Docker configuration
├── tests/                 # Test files
├── docs/                  # Documentation
├── scripts/               # Utility scripts
├── data/                  # Data files
├── tmp/                   # Temporary files (gitignored)
├── .github/               # GitHub Actions workflows
├── pyproject.toml         # Python dependencies and config
├── CLAUDE.md             # Claude Code instructions
├── COMMANDS.md           # Command reference
└── README.md             # Project overview
```

## Key Source Directories

### Clean Architecture Layers
- `src/domain/`: Core business logic
  - `entities/`: Business objects (Speaker, Politician, Meeting, etc.)
  - `repositories/`: Repository interfaces
  - `services/`: Domain services
  - `types/`: Type definitions

- `src/application/`: Application business rules
  - `usecases/`: Use case implementations
  - `dtos/`: Data transfer objects

- `src/infrastructure/`: External concerns
  - `persistence/`: Database implementations
  - `external/`: LLM, storage, scraping services
  - `interfaces/`: Service interfaces

- `src/interfaces/`: User interfaces
  - `streamlit/`: Web UI components
  - `web/`: Other web interfaces
  - `cli/`: (planned migration)

### Legacy/Transitional Code
- `src/database/`: Legacy repository implementations
- `src/streamlit/`: Legacy Streamlit code
- `src/web_scraper/`: Web scraping modules
- `src/models/`: Pydantic models
- `src/services/`: Service layer
- `src/common/`: Shared utilities

### Feature-Specific Modules
- `src/minutes_divide_processor/`: Minutes processing with LangGraph
- `src/party_member_extractor/`: Political party member extraction
- `src/conference_member_extractor/`: Conference member extraction
- `src/parliamentary_group_member_extractor/`: Parliamentary group extraction

### CLI Package
- `src/cli_package/`: CLI command structure
  - `commands/`: Command implementations
  - `base.py`: Base command classes
  - `utils.py`: CLI utilities

## Database Structure
- `database/init.sql`: Initial schema
- `database/migrations/`: Sequential migrations
- `database/02_run_migrations.sql`: Migration runner
- `database/seed_*.sql`: Master data seeds
- `database/backups/`: Backup storage

## Test Structure
Tests mirror source structure:
- `tests/domain/`: Domain layer tests
- `tests/application/`: Use case tests
- `tests/infrastructure/`: Infrastructure tests
- `tests/integration/`: Integration tests
- `tests/common/`: Utility tests

## Configuration Files
- `.env.example`: Environment template
- `pyrightconfig.json`: Type checking config
- `.pre-commit-config.yaml`: Pre-commit hooks
- `.mcp.json`: MCP server configuration
- `docker-compose.yml`: Main Docker config
- `docker-compose.override.yml`: Port overrides (auto-generated)

## Key Entry Points
- `src/cli.py`: Main CLI entry (polibase command)
- `src/streamlit/app.py`: Streamlit UI
- `src/monitoring_app.py`: Monitoring dashboard
- `src/process_minutes.py`: Minutes processing
- `src/extract_speakers_from_minutes.py`: Speaker extraction
