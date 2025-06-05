# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Polibase is a Political Activity Tracking Application (政治活動追跡アプリケーション) for managing and analyzing Japanese political activities including politician statements, meeting minutes, political promises, and voting records.

## Key Commands

### Environment Setup
```bash
# First time setup
cp .env.example .env  # Configure GOOGLE_API_KEY for Gemini API
docker compose up -d
./test-setup.sh

# Install dependencies for local development
uv sync

# Google Cloud Storage setup (optional)
gcloud auth application-default login  # Authenticate for GCS access
# Edit .env to set GCS_BUCKET_NAME and GCS_UPLOAD_ENABLED=true
```

### Running the Application

#### Using the Unified CLI (Recommended)
```bash
# Show all available commands
docker compose exec polibase uv run polibase --help

# Process meeting minutes
docker compose exec polibase uv run polibase process-minutes

# Extract politicians
docker compose exec polibase uv run polibase extract-politicians

# Update speaker links with LLM
docker compose exec polibase uv run polibase update-speakers --use-llm

# Launch meeting management web UI
docker compose exec polibase uv run polibase streamlit

# Scrape meeting minutes from web
docker compose exec polibase uv run polibase scrape-minutes "URL"

# Scrape with Google Cloud Storage upload
docker compose exec polibase uv run polibase scrape-minutes "URL" --upload-to-gcs
docker compose exec polibase uv run polibase scrape-minutes "URL" --upload-to-gcs --gcs-bucket my-bucket

# Batch scrape multiple minutes from kaigiroku.net
docker compose exec polibase uv run polibase batch-scrape --tenant kyoto
docker compose exec polibase uv run polibase batch-scrape --tenant osaka

# Batch scrape with GCS upload
docker compose exec polibase uv run polibase batch-scrape --tenant kyoto --upload-to-gcs
```

#### Direct Module Execution (Legacy)
```bash
# Minutes Division Processing
docker compose exec polibase uv run python -m src.process_minutes

# Politician Extraction Processing
docker compose exec polibase uv run python -m src.extract_politicians

# LLM-based Speaker Matching
docker compose exec polibase uv run python update_speaker_links_llm.py
```

### Testing
```bash
# Run tests
docker compose exec polibase uv run pytest

# Test database connection
docker compose exec polibase uv run python -c "from src.config.database import test_connection; test_connection()"
```

### Database Management
```bash
# Access PostgreSQL
docker compose exec postgres psql -U polibase_user -d polibase_db

# Backup/Restore
./backup-database.sh backup
./backup-database.sh restore database/backups/[filename]

# Reset database
./reset-database.sh
```

## Architecture

### Processing Pipeline
1. **Minutes Divider** (`src/minutes_divide_processor/`): Processes PDF minutes using LangGraph state management and Gemini API to extract individual speeches
2. **Politician Extractor** (`src/politician_extract_processor/`): Identifies politicians from extracted speeches using LangChain and Gemini
3. **Speaker Matching** (`update_speaker_links_llm.py`): Uses hybrid rule-based + LLM matching to link conversations to speaker records
4. **Meeting Management UI** (`src/streamlit_app.py`): Streamlit-based web interface for managing meeting URLs and dates
5. **Web Scraper** (`src/web_scraper/`): Extracts meeting minutes from council websites
   - Supports kaigiroku.net system used by many Japanese local councils
   - Uses Playwright for JavaScript-heavy sites

### Database Design
- **Master Data** (pre-populated via seed files):
  - `governing_bodies`: Government entities (国, 都道府県, 市町村)
  - `conferences`: Legislative bodies and committees  
  - `political_parties`: Political parties
- **Core Tables**:
  - `meetings`, `minutes`, `speakers`, `politicians`, `conversations`, `proposals`
- Repository pattern used for database operations (`src/database/`)

### Technology Stack
- **LLM**: Google Gemini API (gemini-2.0-flash, gemini-1.5-flash) via LangChain
- **Database**: PostgreSQL 15 with SQLAlchemy ORM
- **Package Management**: UV (modern Python package manager)
- **PDF Processing**: pypdfium2
- **Web Scraping**: Playwright, BeautifulSoup4
- **State Management**: LangGraph for complex workflows
- **Testing**: pytest with pytest-asyncio for async tests
- **Cloud Storage**: Google Cloud Storage for scraped data persistence

### Development Patterns
- Docker-first development (all commands run through `docker compose exec`)
- Two-phase processing: Extract conversations → Extract politicians → Match speakers
- Environment variables for configuration (DATABASE_URL differs between Docker/local)
- Modular architecture with shared utilities in `src/common/`

## Important Notes
- **API Key Required**: GOOGLE_API_KEY must be set in .env for Gemini API access
- **Database Persistence**: Default docker-compose.yml uses volumes for persistent storage
- **Master Data**: Governing bodies and conferences are fixed master data, not modified during operation
- **Processing Order**: Always run process-minutes → extract-politicians → update-speakers in sequence
- **File Naming**: Fixed typo in minutes_divider.py (was minutes_dividor.py)
- **Unified CLI**: New `polibase` command provides single entry point for all operations
- **GCS Authentication**: Run `gcloud auth application-default login` before using GCS features
- **GCS Structure**: Files are organized by date: `scraped/YYYY/MM/DD/{council_id}_{schedule_id}.{ext}`