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

# Process minutes from GCS (using meeting ID)
docker compose exec polibase uv run python -m src.process_minutes --meeting-id 123

# Scrape politician information from party websites
docker compose exec polibase uv run polibase scrape-politicians --all-parties

# Update speaker links with LLM
docker compose exec polibase uv run polibase update-speakers --use-llm

# Launch meeting management web UI
docker compose exec polibase uv run polibase streamlit

# Scrape meeting minutes from web
docker compose exec polibase uv run polibase scrape-minutes "URL"

# Scrape with Google Cloud Storage upload (automatically saves GCS URIs to meetings table)
docker compose exec polibase uv run polibase scrape-minutes "URL" --upload-to-gcs
docker compose exec polibase uv run polibase scrape-minutes "URL" --upload-to-gcs --gcs-bucket my-bucket

# Batch scrape multiple minutes from kaigiroku.net
docker compose exec polibase uv run polibase batch-scrape --tenant kyoto
docker compose exec polibase uv run polibase batch-scrape --tenant osaka

# Batch scrape with GCS upload
docker compose exec polibase uv run polibase batch-scrape --tenant kyoto --upload-to-gcs

# Extract speakers from meeting minutes
docker compose exec polibase uv run polibase extract-speakers

# Scrape politician information from party websites
docker compose exec polibase uv run polibase scrape-politicians --all-parties
docker compose exec polibase uv run polibase scrape-politicians --party-id 5
docker compose exec polibase uv run polibase scrape-politicians --all-parties --dry-run

# Conference member extraction (3-step process)
# Step 1: Extract members from conference URLs
docker compose exec polibase uv run polibase extract-conference-members --conference-id 185
docker compose exec polibase uv run polibase extract-conference-members --force  # Re-extract all

# Step 2: Match extracted members with existing politicians
docker compose exec polibase uv run polibase match-conference-members --conference-id 185
docker compose exec polibase uv run polibase match-conference-members  # Process all pending

# Step 3: Create politician affiliations from matched data
docker compose exec polibase uv run polibase create-affiliations --conference-id 185
docker compose exec polibase uv run polibase create-affiliations --start-date 2024-01-01

# Check extraction and matching status
docker compose exec polibase uv run polibase member-status --conference-id 185

# Parliamentary group member extraction
# Extract members from parliamentary group URLs
docker compose exec polibase uv run polibase extract-group-members --group-id 1
docker compose exec polibase uv run polibase extract-group-members --all-groups --dry-run

# List parliamentary groups
docker compose exec polibase uv run polibase list-parliamentary-groups
docker compose exec polibase uv run polibase list-parliamentary-groups --with-members
```

#### Direct Module Execution (Legacy)
```bash
# Minutes Division Processing
docker compose exec polibase uv run python -m src.process_minutes

# Minutes Division Processing from GCS
docker compose exec polibase uv run python -m src.process_minutes --meeting-id 123


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

### Code Formatting and Quality

#### Ruff (Code Formatter and Linter)
```bash
# Format code
docker compose exec polibase uv run --frozen ruff format .

# Check code style
docker compose exec polibase uv run --frozen ruff check .

# Fix auto-fixable issues
docker compose exec polibase uv run --frozen ruff check . --fix
```

**Critical Ruff Rules:**
- Line length: 88 characters
- Import sorting (I001)
- Unused imports removal
- Line wrapping conventions:
  - Strings: use parentheses for multi-line
  - Function calls: multi-line with proper indentation
  - Imports: split into multiple lines when needed

#### Type Checking
```bash
# Run type checking with pyright
docker compose exec polibase uv run --frozen pyright
```

**Requirements:**
- Explicit `None` checks for `Optional` types
- Proper type narrowing for strings
- Version warnings can be ignored if type checks pass

#### Pre-commit Hooks
```bash
# Install pre-commit hooks (first time only)
docker compose exec polibase uv run pre-commit install

# Run pre-commit manually on all files
docker compose exec polibase uv run pre-commit run --all-files

# Update pre-commit hooks to latest versions
docker compose exec polibase uv run pre-commit autoupdate
```

**Pre-commit Configuration:**
- Config file: `.pre-commit-config.yaml`
- Runs automatically on `git commit`
- Tools included:
  - Prettier: for YAML/JSON formatting
  - Ruff: for Python formatting and linting
  - Standard hooks: trailing whitespace, EOF fixer, etc.

**Updating Ruff in pre-commit:**
1. Check latest version on PyPI
2. Update `rev` in `.pre-commit-config.yaml`
3. Commit config changes first before running

### Database Management
```bash
# Access PostgreSQL
docker compose exec postgres psql -U polibase_user -d polibase_db

# Backup/Restore (with GCS support)
docker compose exec polibase uv run polibase database backup               # Backup to local and GCS
docker compose exec polibase uv run polibase database backup --no-gcs      # Backup to local only
docker compose exec polibase uv run polibase database restore backup.sql   # Restore from local
docker compose exec polibase uv run polibase database restore gs://bucket/backup.sql  # Restore from GCS
docker compose exec polibase uv run polibase database list                 # List all backups
docker compose exec polibase uv run polibase database list --no-gcs        # List local backups only

# Legacy backup scripts (local only)
./backup-database.sh backup
./backup-database.sh restore database/backups/[filename]

# Reset database
./reset-database.sh

# Apply new migrations
docker compose exec postgres psql -U polibase_user -d polibase_db -f /docker-entrypoint-initdb.d/migrations/004_add_gcs_uri_to_meetings.sql
```

## Architecture

### System Design Principles

Polibase follows these core design principles:

1. **Politician Information from Party Websites**
   - Politicians data is obtained from political party websites
   - Regular updates to maintain current information
   - Structured extraction of names, positions, districts, etc.

2. **Speakers and Speech Content from Meeting Minutes**
   - Speaker names and their statements are extracted from meeting minutes
   - Maintains conversation context and sequence
   - Stores as structured data in `conversations` and `speakers` tables

3. **Speaker-Politician Matching via LLM**
   - Uses LLM to handle name variations and honorifics
   - Hybrid approach combining rule-based and LLM matching
   - High-accuracy linking between `speakers` and `politicians`

4. **Parliamentary Groups (議員団) Management**
   - Parliamentary groups represent voting blocs within conferences
   - Tracks group membership history with roles (団長, 幹事長, etc.)
   - Links proposals voting to both individual politicians and their groups

5. **Conference Member Extraction with Staged Processing**
   - Extract conference members from members_introduction_url in stages
   - Staging table (`extracted_conference_members`) for intermediate data
   - LLM-based fuzzy matching with confidence scores
   - Manual review capability before creating final affiliations

6. **Data Input through Streamlit UI**
   - Party member list URLs managed through web interface
   - Meeting minutes URLs registered and managed
   - Conference members introduction URLs managed
   - User-friendly interface for all data entry

### Processing Pipeline

#### Standard Flow (from PDF)
1. **Minutes Divider** (`src/minutes_divide_processor/`): Processes PDF minutes using LangGraph state management and Gemini API to extract individual speeches
2. **Speaker Extraction** (`src/extract_speakers_from_minutes.py`): Extracts speaker information from conversations and creates speaker records
3. **Speaker Matching** (`update_speaker_links_llm.py`): Uses hybrid rule-based + LLM matching to link conversations to speaker records
4. **Politician Data Collection** (`polibase scrape-politicians`): Fetches latest politician information from party websites

#### Web Scraping Flow (with GCS Integration)
1. **Web Scraper** (`src/web_scraper/`): Extracts meeting minutes from council websites
   - Supports kaigiroku.net system used by many Japanese local councils
   - Uses Playwright for JavaScript-heavy sites
   - Automatically uploads to GCS when `--upload-to-gcs` flag is used
   - Saves GCS URIs to meetings table for later processing
2. **GCS-based Processing**: Minutes Divider can fetch data directly from GCS using `--meeting-id` parameter
3. **Subsequent Processing**: Same as standard flow (speaker extraction, speaker matching)

#### Conference Member Extraction Flow (Staged Processing)
1. **Extract Conference Members** (`extract-conference-members`): Scrapes member information from conference URLs
   - Uses Playwright + LLM to extract member names, roles, and party affiliations
   - Saves to staging table `extracted_conference_members` with status 'pending'
2. **Match with Politicians** (`match-conference-members`): LLM-based fuzzy matching
   - Searches existing politicians by name and party
   - Uses LLM to handle name variations and determine best match
   - Updates matching status: matched (≥0.7), needs_review (0.5-0.7), no_match (<0.5)
3. **Create Affiliations** (`create-affiliations`): Creates final politician-conference relationships
   - Only processes 'matched' status records
   - Creates entries in `politician_affiliations` with roles

#### Additional Components
- **Meeting Management UI** (`src/streamlit_app.py`): Streamlit-based web interface for managing meeting URLs, dates, and political party information
- **Party Member Extractor** (`src/party_member_extractor/`): LLM-based extraction of politician information from party member list pages
  - Uses Gemini API to extract structured data from HTML
  - Supports pagination for multi-page member lists
  - Implements duplicate checking to prevent creating duplicate records
- **Conference Member Extractor** (`src/conference_member_extractor/`): Staged extraction and matching of conference members
  - Staging table for intermediate data review
  - Confidence-based matching with manual review capability

### Database Design
- **Master Data** (pre-populated via seed files):
  - `governing_bodies`: Government entities (国, 都道府県, 市町村)
  - `conferences`: Legislative bodies and committees
  - `political_parties`: Political parties (includes `members_list_url` for web scraping)
- **Core Tables**:
  - `meetings`: Includes `gcs_pdf_uri` and `gcs_text_uri` for GCS integration
  - `minutes`, `speakers`, `politicians`, `conversations`, `proposals`
  - `politicians` table includes party affiliation and profile information
  - `politician_affiliations`: Conference memberships with roles
  - `extracted_conference_members`: Staging table for member extraction
  - `parliamentary_groups`: Parliamentary groups (議員団/会派) within conferences
  - `parliamentary_group_memberships`: Tracks politician membership in groups over time
- Repository pattern used for database operations (`src/database/`)
- Migrations in `database/migrations/` for schema updates:
  - `004_add_gcs_uri_to_meetings.sql`: Adds GCS URI columns to meetings table
  - `005_add_members_introduction_url_to_conferences.sql`: Adds member URL to conferences
  - `006_add_role_to_politician_affiliations.sql`: Adds role column for positions
  - `007_create_extracted_conference_members_table.sql`: Creates staging table
  - `008_create_parliamentary_groups_tables.sql`: Creates parliamentary groups and membership tables

### Technology Stack
- **LLM**: Google Gemini API (gemini-2.0-flash, gemini-1.5-flash) via LangChain
- **Database**: PostgreSQL 15 with SQLAlchemy ORM
- **Package Management**: UV (modern Python package manager)
- **PDF Processing**: pypdfium2
- **Web Scraping**: Playwright, BeautifulSoup4
- **State Management**: LangGraph for complex workflows
- **Testing**: pytest with pytest-asyncio for async tests
- **Cloud Storage**: Google Cloud Storage for scraped data persistence
  - GCSStorage utility supports both upload and download operations
  - Handles GCS URI format: `gs://bucket-name/path/to/file`

### Development Patterns
- Docker-first development (all commands run through `docker compose exec`)
- Multi-phase processing: Extract conversations → Extract speakers → Match speakers → Scrape party members from websites
- Environment variables for configuration (DATABASE_URL differs between Docker/local)
- Modular architecture with shared utilities in `src/common/`
- Async/await pattern for web scraping operations
- Upsert pattern for politician data to prevent duplicates

## Important Notes
- **API Key Required**: GOOGLE_API_KEY must be set in .env for Gemini API access
- **Database Persistence**: Default docker-compose.yml uses volumes for persistent storage
- **Master Data**: Governing bodies and conferences are fixed master data, not modified during operation
- **Processing Order**: Always run process-minutes → extract-speakers → update-speakers in sequence
- **File Naming**: Fixed typo in minutes_divider.py (was minutes_dividor.py)
- **Unified CLI**: New `polibase` command provides single entry point for all operations
- **GCS Authentication**: Run `gcloud auth application-default login` before using GCS features
- **GCS Structure**: Files are organized by date: `scraped/YYYY/MM/DD/{council_id}_{schedule_id}.{ext}`
- **GCS Integration**: Web scraper automatically saves GCS URIs to meetings table when uploading
- **GCS-based Processing**: Minutes divider can fetch text directly from GCS using meeting ID
- **Party Member Scraping**: Before scraping, set `members_list_url` for parties via Streamlit UI's "政党管理" tab
- **Playwright Dependencies**: Docker image includes Chromium and dependencies for web scraping
- **Duplicate Prevention**: Politician scraper checks existing records by name + party to avoid duplicates
- **Database Migrations**: Run migrations after pulling updates that modify database schema
- **GCS URI Format**: Always use `gs://` format for GCS URIs, not HTTPS URLs
