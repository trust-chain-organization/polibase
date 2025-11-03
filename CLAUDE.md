# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Polibase is a Political Activity Tracking Application (政治活動追跡アプリケーション) for managing and analyzing Japanese political activities including politician statements, meeting minutes, political promises, and voting records.

## Key Commands

For comprehensive command reference including setup, application execution, testing, code quality, and database management, see:

**📖 [Command Reference](.claude/skills/polibase-commands/)**

### Quick Start

```bash
# First time setup
cp .env.example .env  # Configure GOOGLE_API_KEY
just up               # Start environment

# Run application
just streamlit        # Launch web UI
just monitoring       # Launch monitoring dashboard
just bi-dashboard     # Launch BI Dashboard (Plotly Dash)

# Development
just test             # Run tests
just format && just lint  # Format and lint code

# Database
just db               # Connect to PostgreSQL
./reset-database.sh   # Reset database
```

### Most Common Commands

```bash
just up                                    # Start containers
just exec uv run polibase streamlit        # Launch Streamlit UI
just bi-dashboard                          # Launch BI Dashboard (Plotly Dash)
just exec uv run polibase process-minutes  # Process meeting minutes
just exec uv run polibase scrape-politicians --all-parties  # Scrape politicians
just test                                  # Run tests with type checking
just format                                # Format code
just db                                    # Connect to database
just down                                  # Stop containers
```

For detailed command documentation with all options, workflows, and examples, see `.claude/skills/polibase-commands/reference.md`.

### Testing Guidelines
- **外部サービスへの依存を避ける**: テストでは外部LLMサービス（Google Gemini API）やその他のAPIに実際にアクセスしてはいけません
- **モックの使用**: 外部サービスとの連携をテストする場合は、必ずモックを使用してください
- **テストの独立性**: テストは環境（CI/ローカル）に依存せず、常に同じ結果を返すようにしてください

## Architecture

> 📚 **Visual Diagrams**: See [docs/diagrams/](docs/diagrams/) for detailed architecture diagrams
> 📖 **Full Documentation**: See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for comprehensive architecture guide
> ☁️ **Cloud Architecture**: For Google Cloud Platform deployment design, see the [Cloud Architecture section](docs/ARCHITECTURE.md#クラウドアーキテクチャ-google-cloud-platform) in ARCHITECTURE.md

**Important**: The sections below provide an overview. For detailed information including:
- Complete layer descriptions and component interactions
- Data flow diagrams and sequence flows
- Security architecture and network design
- **Google Cloud Platform deployment architecture** (Cloud Run, Cloud SQL, Vertex AI, etc.)
- Cost estimation and optimization strategies
- Disaster recovery and deployment procedures

Please refer to **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

### Clean Architecture Implementation

Polibase has successfully migrated to Clean Architecture. **Status: 🟢 98% Complete**

The architecture separates concerns into distinct layers following the Dependency Inversion Principle.

### Quick Reference Diagrams

**Essential diagrams for understanding the system**:
- [Layer Dependency](docs/diagrams/layer-dependency.mmd) - Shows how layers depend on each other
- [Component Interaction](docs/diagrams/component-interaction.mmd) - End-to-end request flow
- [Minutes Processing Flow](docs/diagrams/data-flow-minutes-processing.mmd) - How議事録 are processed
- [Speaker Matching Flow](docs/diagrams/data-flow-speaker-matching.mmd) - How speakers are matched with politicians
- [Politician Scraping Flow](docs/diagrams/data-flow-politician-scraping.mmd) - How politician data is scraped
- [Repository Pattern](docs/diagrams/repository-pattern.mmd) - Data access layer implementation

#### Layer Structure

1. **Domain Layer** (`src/domain/`) - ✅ Complete (77 files)
   - **Entities** (21 files): Core business objects with business rules
     - `BaseEntity`: Common fields and methods for all entities
     - Business entities: `Politician`, `Speaker`, `Meeting`, `Conference`, `Proposal`, etc.
   - **Repository Interfaces** (22 files): Abstract interfaces for data access
     - `BaseRepository[T]`: Generic repository with common CRUD operations
     - `ISessionAdapter`: Database session abstraction (Issue #592: now complete with `get()` and `delete()` methods)
     - Entity-specific repositories with additional query methods
   - **Domain Services** (18 files): Business logic that doesn't belong to entities
     - `SpeakerDomainService`: Name normalization, party extraction, similarity calculation
     - `PoliticianDomainService`: Deduplication, validation, merging logic
     - `MinutesDomainService`: Text processing, conversation extraction
     - `ConferenceDomainService`: Member role extraction
     - `ParliamentaryGroupDomainService`: Group membership validation
     - `SpeakerMatchingService`, `PoliticianMatchingService`: Matching algorithms
   - **Service Interfaces** (8 files): External service abstractions
     - `ILLMService`, `IStorageService`, `IWebScraperService`, `ITextExtractorService`, etc.

2. **Application Layer** (`src/application/`) - ✅ Complete (37 files)
   - **Use Cases** (21 files): Application-specific business rules
     - `ProcessMinutesUseCase`: Orchestrates minutes processing workflow
     - `MatchSpeakersUseCase`: Speaker-politician matching coordination
     - `ScrapePoliticiansUseCase`: Party member scraping workflow
     - `ManageConferenceMembersUseCase`: Conference member management
     - `Extract*UseCase`, `Manage*UseCase`: Various data processing and management
   - **DTOs** (16 files): Data Transfer Objects for clean layer separation
     - Input/Output DTOs for each use case
     - Prevents domain model leakage to outer layers
     - Includes validation logic

3. **Infrastructure Layer** (`src/infrastructure/`) - ✅ Complete (63 files)
   - **Persistence** (22+ files): Database access implementations
     - `BaseRepositoryImpl[T]`: Generic SQLAlchemy repository using `ISessionAdapter`
     - All 22 domain repositories have corresponding implementations
     - `AsyncSessionAdapter`: Adapts sync sessions for async usage
     - `UnitOfWorkImpl`: Transaction management implementation
   - **External Services**: Third-party integrations
     - `GeminiLLMService`: Google Gemini API integration
     - `CachedLLMService`, `InstrumentedLLMService`: Decorator pattern for caching and instrumentation
     - `GCSStorageService`: Google Cloud Storage integration
     - `WebScraperService`: Playwright-based web scraping
     - `MinutesProcessingService`, `ProposalScraperService`: Domain-specific services
   - **Infrastructure Support**:
     - DI Container (`di/`): Dependency injection
     - Logging (`logging/`): Structured logging
     - Monitoring (`monitoring/`): Performance metrics
     - Error Handling (`error_handling/`): Centralized error management

4. **Interfaces Layer** (`src/interfaces/`) - ✅ Mostly Complete (63 files)
   - **CLI** (`src/interfaces/cli/`): Command-line interfaces
     - Unified `polibase` command entry point
     - Structured commands: `scraping/`, `database/`, `processing/`, `monitoring/`
   - **Web** (`src/interfaces/web/streamlit/`): Streamlit UI
     - `views/`: Page views for各entity types
     - `presenters/`: Business logic presentation layer
     - `components/`: Reusable UI components
     - `dto/`: UI-specific data transfer objects
     - Complete separation of business logic from UI

#### Migration Status

**Overall: 🟢 100% Complete** ✅

| Layer | Files | Status |
|-------|-------|--------|
| Domain | 77 | ✅ 100% |
| Application | 37 | ✅ 100% |
| Infrastructure | 63 | ✅ 100% |
| Interfaces | 63 | ✅ 100% |
| **Legacy Cleanup** | ~20 | ✅ 100% |

**Completed**:
- ✅ All 22 domain repositories have infrastructure implementations
- ✅ All 21 use cases implemented
- ✅ Full async/await support across all repositories
- ✅ Complete dependency inversion (Domain ← Infrastructure)
- ✅ `ISessionAdapter` complete with `get()` and `delete()` (Issue #592)
- ✅ CLI fully migrated to `src/interfaces/cli/` (Issue #641, Phase 5/5)
- ✅ Web UI migrated to `src/interfaces/web/streamlit/`
- ✅ Legacy Streamlit directories removed (`src/streamlit/`, `src/interfaces/streamlit/`) (Issue #602)
- ✅ `src/models/` directory completely removed (Issue #640, Phase 4/5)
  - All DTOs migrated to `src/application/dtos/`
  - All entities migrated to `src/domain/entities/`
  - All tests updated to use domain entities and DTOs
- ✅ `src/cli_package/` completely migrated to `src/interfaces/cli/` (Issue #641, Phase 5/5)
- ✅ All deprecated files removed (cli.py, exceptions.py, process_minutes.py, monitoring_app.py)
- ✅ All backward compatibility stubs removed
- ✅ 100% Clean Architecture compliance achieved

See:
- [CLEAN_ARCHITECTURE_MIGRATION.md](docs/CLEAN_ARCHITECTURE_MIGRATION.md) - Migration guide
- [tmp/clean_architecture_analysis_2025.md](tmp/clean_architecture_analysis_2025.md) - Detailed analysis

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
- **Meeting Management UI** (`src/interfaces/web/streamlit/`): Streamlit-based web interface with URL routing for managing meetings, parties, conferences, and more
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
- **CI/CDでのテストスキップ**: テストやチェックを`continue-on-error: true`でスキップする場合は、必ず対応するIssueを作成すること
  - スキップした理由を明確に記載
  - 修正方法を具体的に記述
  - 関連するPRやIssueをリンク
  - 優先度を適切に設定（通常は高優先度）
- **Pre-commit Hooks遵守**: **絶対に `--no-verify` オプションを使用してpre-commit hooksを回避しないでください**
  - pre-commit hooksがfailした場合は、必ずエラーを修正してからコミットしてください
  - ruff、pyright、prettier等のチェックが通らない場合は、コードを修正してください
  - 一時的な回避が必要な場合は、設定ファイル（pyproject.toml等）で適切に除外設定を追加してください
  - `git commit --no-verify` は使用禁止です
- **知識蓄積層の活用** (`_docs/`): 開発過程での思考や判断を適切に記録してください
  - **いつ使うか**:
    - 技術的な選択で迷った時 → `_docs/thinking/` に設計判断を記録
    - 新機能を実装した時 → `_docs/features/` に実装の目的と完了条件を記録
    - ファイルやディレクトリを削除した時 → `_docs/deleted/` に削除理由と影響を記録
  - **記録のタイミング**: 判断した直後（記憶が鮮明なうちに）
  - **記録内容のポイント**:
    - 短く簡潔に（長文は避ける）
    - 箇条書きを活用
    - 将来のClaude（または開発者）が理解できる言葉で書く
    - 客観的な事実と主観的な判断を区別する
  - **ファイル命名規則**: `YYYY-MM-DD_簡潔な説明.md` (例: `2025-01-15_api_design_decision.md`)
  - **テンプレート**: 各ディレクトリの `README.md` を参照
  - **注意**: この `_docs/` ディレクトリは `.gitignore` に含まれており、Gitリポジトリには含まれません
  - **公式ドキュメントとの違い**: チーム全体で共有すべき情報は `docs/` ディレクトリに記載してください
