# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Polibase is a Political Activity Tracking Application (政治活動追跡アプリケーション) for managing and analyzing Japanese political activities including politician statements, meeting minutes, political promises, and voting records.

## Key Commands

### Environment Setup
```bash
# First time setup
cp .env.example .env  # Configure GOOGLE_API_KEY for Gemini API

# Docker起動（重要: docker-compose.override.ymlがある場合は必ず両方を指定）
# git worktreeを使用している場合:
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml up -d
# 通常の場合（override.ymlがない場合）:
docker compose -f docker/docker-compose.yml up -d

./test-setup.sh

# Install dependencies for local development
uv sync

# Google Cloud Storage setup (optional)
gcloud auth application-default login  # Authenticate for GCS access
# Edit .env to set GCS_BUCKET_NAME and GCS_UPLOAD_ENABLED=true
```

#### Port Configuration with docker-compose.override.yml
git worktreeを使用している場合、`docker/docker-compose.override.yml`が自動生成されポート番号が上書きされます：
- このファイルは各worktreeで異なるポート番号を使用し、ポートの衝突を防ぎます
- 実際のポート番号は`docker ps`で確認するか、`docker/docker-compose.override.yml`を参照してください
- 例: Streamlitが9291番、APIが8790番、Monitoringが9292番など（worktreeによって異なります）
- コンテナ内部のポート番号（8501など）は変わりませんが、ホストからアクセスする際のポート番号が変更されます

**重要**:
1. **必ずdocker-compose.override.ymlも指定**: git worktreeを使用している場合は、すべてのdocker composeコマンドで`-f docker/docker-compose.override.yml`を追加してください
2. **ポート番号の確認**: 実際のポート番号は`docker ps`または`docker/docker-compose.override.yml`で確認してください

### Running the Application

#### Using the Unified CLI (Recommended)
```bash
# Show all available commands
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase --help

# Process meeting minutes
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase process-minutes

# Process minutes from GCS (using meeting ID)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run python -m src.process_minutes --meeting-id 123

# Scrape politician information from party websites
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase scrape-politicians --all-parties

# Update speaker links with LLM
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase update-speakers --use-llm

# Launch meeting management web UI
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase streamlit

# Launch monitoring dashboard for data coverage visualization
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase monitoring

# Scrape meeting minutes from web
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase scrape-minutes "URL"

# Scrape with Google Cloud Storage upload (automatically saves GCS URIs to meetings table)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase scrape-minutes "URL" --upload-to-gcs
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase scrape-minutes "URL" --upload-to-gcs --gcs-bucket my-bucket

# Batch scrape multiple minutes from kaigiroku.net
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase batch-scrape --tenant kyoto
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase batch-scrape --tenant osaka

# Batch scrape with GCS upload
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase batch-scrape --tenant kyoto --upload-to-gcs

# Extract speakers from meeting minutes
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase extract-speakers

# Scrape politician information from party websites
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase scrape-politicians --all-parties
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase scrape-politicians --party-id 5
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase scrape-politicians --all-parties --dry-run

# Conference member extraction (3-step process)
# Step 1: Extract members from conference URLs
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase extract-conference-members --conference-id 185
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase extract-conference-members --force  # Re-extract all

# Step 2: Match extracted members with existing politicians
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase match-conference-members --conference-id 185
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase match-conference-members  # Process all pending

# Step 3: Create politician affiliations from matched data
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase create-affiliations --conference-id 185
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase create-affiliations --start-date 2024-01-01

# Check extraction and matching status
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase member-status --conference-id 185

# Show coverage statistics for governing bodies
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase coverage
```

#### Direct Module Execution (Legacy)
```bash
# Minutes Division Processing
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run python -m src.process_minutes

# Minutes Division Processing from GCS
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run python -m src.process_minutes --meeting-id 123


# LLM-based Speaker Matching
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run python update_speaker_links_llm.py
```

### Testing
```bash
# Run tests
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run pytest

# Test database connection
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run python -c "from src.config.database import test_connection; test_connection()"

# Run LLM evaluation tests (local - uses mock by default)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase evaluate --all
# Note: Evaluation tests are excluded from CI to save API costs
# Run manually via GitHub Actions workflow_dispatch for real LLM testing
```

#### Testing Guidelines
- **外部サービスへの依存を避ける**: テストでは外部LLMサービス（Google Gemini API）やその他のAPIに実際にアクセスしてはいけません
- **モックの使用**: 外部サービスとの連携をテストする場合は、必ずモックを使用してください
  - LLMサービスのレスポンスはモックで作成
  - APIキーの検証もモックで実施
  - ネットワーク接続は不要
- **テストの独立性**: テストは環境（CI/ローカル）に依存せず、常に同じ結果を返すようにしてください
- **統合テスト**: 実際のサービスとの統合をテストする必要がある場合は、別途手動テストとして実施し、自動テストには含めません

### Code Formatting and Quality

#### Ruff (Code Formatter and Linter)
```bash
# Format code
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run --frozen ruff format .

# Check code style
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run --frozen ruff check .

# Fix auto-fixable issues
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run --frozen ruff check . --fix
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
# NOTE: pyrightを実行する際は、Dockerコンテナ内ではなくローカル環境で実行してください
# Docker環境では設定ファイルの読み込みに問題が発生することがあります
uv run --frozen pyright

# 特定のフォルダのみチェックする場合
uv run --frozen pyright src/database/

# pyrightの出力が多い場合、特定のフォルダのエラーのみを抽出
uv run --frozen pyright 2>&1 | grep -A5 -B5 "src/database/"
```

**Requirements:**
- Explicit `None` checks for `Optional` types
- Proper type narrowing for strings
- Version warnings can be ignored if type checks pass
- pyrightconfig.json で設定されたルールに従う

#### Pre-commit Hooks
```bash
# Install pre-commit hooks (first time only)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run pre-commit install

# Run pre-commit manually on all files
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run pre-commit run --all-files

# Update pre-commit hooks to latest versions
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run pre-commit autoupdate
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
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec postgres psql -U polibase_user -d polibase_db

# Backup/Restore (with GCS support)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase database backup               # Backup to local and GCS
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase database backup --no-gcs      # Backup to local only
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase database restore backup.sql   # Restore from local
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase database restore gs://bucket/backup.sql  # Restore from GCS
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase database list                 # List all backups
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase uv run polibase database list --no-gcs        # List local backups only

# Legacy backup scripts (local only)
./backup-database.sh backup
./backup-database.sh restore database/backups/[filename]

# Reset database
./reset-database.sh

# Apply new migrations manually (if needed)
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec polibase cat /app/database/migrations/013_create_llm_processing_history.sql | docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml exec -T postgres psql -U polibase_user -d polibase_db

# Important: When adding new migration files
# 1. Create migration file in database/migrations/ with sequential numbering (e.g., 016_*.sql)
# 2. Add the migration to database/02_run_migrations.sql to ensure it runs on reset-database.sh
```

## Architecture

### Clean Architecture Implementation

Polibase has successfully migrated to Clean Architecture (Phase 3 cleanup in progress). The architecture separates concerns into distinct layers:

#### Layer Structure

1. **Domain Layer** (`src/domain/`)
   - **Entities**: Core business objects with business rules
     - `BaseEntity`: Common fields and methods for all entities
     - Business entities: GoverningBody, Conference, Meeting, Politician, Speaker, etc.
   - **Repository Interfaces**: Abstract interfaces for data access
     - `BaseRepository[T]`: Generic repository with common CRUD operations
     - Entity-specific repositories with additional methods
   - **Domain Services**: Business logic that doesn't belong to entities
     - `SpeakerDomainService`: Name normalization, party extraction, similarity
     - `PoliticianDomainService`: Deduplication, validation, merging
     - `MinutesDomainService`: Text processing, conversation extraction
     - `ConferenceDomainService`: Member role extraction
     - `ParliamentaryGroupDomainService`: Group membership validation

2. **Application Layer** (`src/application/`)
   - **Use Cases**: Application-specific business rules
     - `ProcessMinutesUseCase`: Orchestrates minutes processing workflow
     - `MatchSpeakersUseCase`: Speaker-politician matching coordination
     - `ScrapePoliticiansUseCase`: Party member scraping workflow
     - `ManageConferenceMembersUseCase`: Conference member management
   - **DTOs**: Data Transfer Objects for clean layer separation
     - Input/Output DTOs for each use case
     - Prevents domain model leakage to outer layers

3. **Infrastructure Layer** (`src/infrastructure/`)
   - **Persistence**: Database access implementations
     - `BaseRepositoryImpl`: Generic SQLAlchemy repository
     - Entity-specific implementations
   - **External Services**: Third-party integrations
     - `ILLMService` / `GeminiLLMService`: LLM integration
     - `IStorageService` / `GCSStorageService`: Cloud storage
     - `IWebScraperService` / `PlaywrightScraperService`: Web scraping

4. **Interfaces Layer** (`src/interfaces/`)
   - **CLI**: Command-line interfaces (migration in progress)
   - **Web**: Streamlit UI (migration in progress)

#### Migration Status

Clean Architecture migration is nearly complete (Phase 3: Legacy cleanup):
- ✅ All core repositories migrated to infrastructure layer
- ✅ Domain entities and services implemented
- ✅ Use cases and DTOs created
- ⏳ Removing remaining legacy files (6 files left)
- See [CLEAN_ARCHITECTURE_MIGRATION.md](docs/CLEAN_ARCHITECTURE_MIGRATION.md) for details

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
- **Meeting Management UI** (`src/streamlit/`): Streamlit-based web interface with URL routing for managing meetings, parties, conferences, and more
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
- Repository pattern with Clean Architecture (`src/infrastructure/persistence/`)
- Migrations in `database/migrations/` for schema updates:
  - `004_add_gcs_uri_to_meetings.sql`: Adds GCS URI columns to meetings table
  - `005_add_members_introduction_url_to_conferences.sql`: Adds member URL to conferences
  - `006_add_role_to_politician_affiliations.sql`: Adds role column for positions
  - `007_create_extracted_conference_members_table.sql`: Creates staging table
  - `008_create_parliamentary_groups_tables.sql`: Creates parliamentary groups and membership tables
  - `011_add_organization_code_to_governing_bodies.sql`: Adds organization_code and organization_type for tracking coverage

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
- **Data Visualization**:
  - Plotly for interactive charts
  - Folium for interactive Japan map visualization
  - Streamlit for dashboard UI

### Development Patterns
- Docker-first development (all commands run through `docker compose -f docker/docker-compose.yml [-f docker/docker-compose.override.yml] exec`)
- Multi-phase processing: Extract conversations → Extract speakers → Match speakers → Scrape party members from websites
- Environment variables for configuration (DATABASE_URL differs between Docker/local)
- Modular architecture with shared utilities in `src/common/`
- Async/await pattern for web scraping operations
- Upsert pattern for politician data to prevent duplicates

#### Clean Architecture Guidelines
- **Dependency Rule**: Dependencies must point inward (Domain ← Application ← Infrastructure ← Interfaces)
- **Entity Independence**: Domain entities should not depend on external frameworks or libraries
- **Interface Segregation**: Repository interfaces should be minimal and focused
- **Async Repositories**: All repository methods use async/await for consistency
- **DTO Usage**: Always use DTOs for data transfer between layers
- **Service Injection**: Use dependency injection pattern in use cases
- **Type Safety**: Leverage Python 3.11+ type hints throughout
- **Testing**: Write unit tests for domain services and use cases

#### When Adding New Features
1. Start with domain entities and services
2. Define repository interfaces needed
3. Create use cases in application layer
4. Implement infrastructure (repositories, external services)
5. Add interface layer last (CLI/Web)
6. Write tests at each layer

## Documentation

### Key Documentation Files and Their Locations

When working on this project, refer to these documentation files for detailed information:

#### Architecture Documentation
- **Clean Architecture Migration**: `docs/CLEAN_ARCHITECTURE_MIGRATION.md`
  - Migration progress tracking
  - Module-by-module migration status
  - Implementation guidelines

- **Database Schema**: `docs/DATABASE_SCHEMA.md`
  - Complete database structure
  - Table relationships
  - Column descriptions

- **API Documentation**: `docs/API_DOCUMENTATION.md`
  - API endpoints specification
  - Request/response formats
  - Authentication details

#### Development Guides
- **Development Guide**: `docs/DEVELOPMENT_GUIDE.md`
  - Setup instructions
  - Development workflow
  - Coding standards

- **Testing Guide**: `docs/TESTING_GUIDE.md`
  - Test structure
  - Testing strategies
  - Running tests

#### Domain Documentation
- **Domain Model**: `docs/DOMAIN_MODEL.md`
  - Business entities
  - Domain services
  - Business rules

- **Use Cases**: `docs/USE_CASES.md`
  - Application use cases
  - Business workflows
  - User scenarios

#### Infrastructure Documentation
- **Deployment**: `docs/DEPLOYMENT.md`
  - Deployment procedures
  - Environment configuration
  - Production setup

- **Monitoring**: `docs/MONITORING.md`
  - Monitoring setup
  - Metrics collection
  - Alert configuration

#### Quick Reference Files
- **Environment Variables**: `.env.example`
  - Required environment variables
  - Configuration options

- **Project Dependencies**: `pyproject.toml`
  - Python dependencies
  - Development tools configuration

- **Docker Configuration**: `docker/docker-compose.yml`
  - Container setup
  - Service definitions

- **Database Migrations**: `database/migrations/`
  - Schema migration files
  - Sequential update scripts

#### Code Organization
- **Source Code**: `src/`
  - `domain/` - Domain entities and business logic
  - `application/` - Use cases and DTOs
  - `infrastructure/` - External service implementations
  - `interfaces/` - User interfaces (CLI, Web)

- **Tests**: `tests/`
  - Unit tests organized by module
  - Integration tests
  - Evaluation tests

## Important Notes
- **API Key Required**: GOOGLE_API_KEY must be set in .env for Gemini API access
- **Database Persistence**: Docker Compose configuration at docker/docker-compose.yml uses volumes for persistent storage
- **Master Data**: Governing bodies and conferences are fixed master data, not modified during operation
- **Coverage Tracking**: All Japanese municipalities (1,966 entities) are now tracked in governing_bodies table with organization codes
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
- **Database Migrations**:
  - Run migrations after pulling updates that modify database schema
  - When creating new migration files:
    1. Create in `database/migrations/` with sequential numbering (e.g., `016_*.sql`)
    2. **必ず** `database/02_run_migrations.sql` に追加して、`reset-database.sh` 実行時に適用されるようにする
- **GCS URI Format**: Always use `gs://` format for GCS URIs, not HTTPS URLs
- **Intermediate Files**: Always create temporary or intermediate files (including markdown files for planning, summaries, etc.) in the `tmp/` directory. This directory is gitignored to keep the repository clean
- **UI Testing with Playwright**: When testing or verifying Streamlit UI behavior, use Playwright MCP tools (`mcp__playwright__*`) to:
  - Navigate to the Streamlit app (check actual port with `docker ps` or `docker/docker-compose.override.yml`)
  - Take screenshots to verify UI changes
  - Interact with UI elements to test functionality
  - Capture and verify error messages or success notifications
- **CI/CDでのテストスキップ**: テストやチェックを`continue-on-error: true`でスキップする場合は、必ず対応するIssueを作成すること
  - スキップした理由を明確に記載
  - 修正方法を具体的に記述
  - 関連するPRやIssueをリンク
  - 優先度を適切に設定（通常は高優先度）
