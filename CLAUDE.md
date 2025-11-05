# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language Preference

**IMPORTANT: このプロジェクトでは、すべての説明、コメント、ドキュメントを日本語で記述してください。**

- コードのコメント: 日本語で記述
- Git commitメッセージ: 日本語で記述
- ドキュメント: 日本語で記述
- Claude Codeとのやり取り: 日本語で応答

This project primarily uses Japanese for all documentation, comments, and communication.

## Project Overview

Polibase is a Political Activity Tracking Application (政治活動追跡アプリケーション) for managing and analyzing Japanese political activities including politician statements, meeting minutes, political promises, and voting records.

### Core Concepts

- **Politician Information**: Scraped from political party websites
- **Speakers & Speeches**: Extracted from meeting minutes
- **Speaker-Politician Matching**: LLM-based matching with hybrid approach
- **Parliamentary Groups**: Voting blocs within conferences
- **Staged Processing**: Multi-step workflows with manual review capability

## Quick Start

```bash
# First time setup
cp .env.example .env  # Configure GOOGLE_API_KEY
just up               # Start environment

# Run application
just streamlit        # Launch web UI
just bi-dashboard     # Launch BI Dashboard

# Development
just test             # Run tests
just format && just lint  # Format and lint code

# Database
just db               # Connect to PostgreSQL
./reset-database.sh   # Reset database
```

**📖 For detailed commands**: See [.claude/skills/polibase-commands/](.claude/skills/polibase-commands/)

## Architecture

Polibase follows **Clean Architecture** principles. **Status: 🟢 100% Complete**

### Layer Overview

```
src/
├── domain/          # Entities, Repository Interfaces, Domain Services (77 files)
├── application/     # Use Cases, DTOs (37 files)
├── infrastructure/  # Repository Implementations, External Services (63 files)
└── interfaces/      # CLI, Web UI (63 files)
```

### Key Principles

- **Dependency Rule**: Dependencies point inward (Domain ← Application ← Infrastructure ← Interfaces)
- **Entity Independence**: Domain entities have no framework dependencies
- **Repository Pattern**: All repositories use async/await with `ISessionAdapter`
- **DTO Usage**: DTOs for layer boundaries

**📖 For detailed architecture**: See [.claude/skills/clean-architecture-checker/](.claude/skills/clean-architecture-checker/)

### Visual Diagrams

- [Layer Dependency](docs/diagrams/layer-dependency.mmd)
- [Component Interaction](docs/diagrams/component-interaction.mmd)
- [Minutes Processing Flow](docs/diagrams/data-flow-minutes-processing.mmd)
- [Speaker Matching Flow](docs/diagrams/data-flow-speaker-matching.mmd)
- [Repository Pattern](docs/diagrams/repository-pattern.mmd)

**📖 Full documentation**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Technology Stack

- **LLM**: Google Gemini API (gemini-2.0-flash, gemini-1.5-flash) via LangChain
- **Database**: PostgreSQL 15 with SQLAlchemy ORM
- **Package Management**: UV (modern Python package manager)
- **PDF Processing**: pypdfium2
- **Web Scraping**: Playwright, BeautifulSoup4
- **State Management**: LangGraph for complex workflows
- **Testing**: pytest with pytest-asyncio
- **Cloud Storage**: Google Cloud Storage
- **Data Visualization**: Plotly, Folium, Streamlit

## Key Skills

Polibaseプロジェクトでは、以下のスキルが自動的にアクティベートされます：

- **[data-processing-workflows](.claude/skills/data-processing-workflows/)**: データ処理パイプラインとワークフロー
- **[clean-architecture-checker](.claude/skills/clean-architecture-checker/)**: Clean Architectureの原則とレイヤー構造
- **[test-writer](.claude/skills/test-writer/)**: テスト作成ガイドとTDD
- **[migration-helper](.claude/skills/migration-helper/)**: データベース移行とスキーマ管理
- **[project-conventions](.claude/skills/project-conventions/)**: プロジェクト規約とベストプラクティス
- **[development-workflows](.claude/skills/development-workflows/)**: 開発ワークフローとパターン

## Documentation

### Architecture & Development
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Complete system architecture
- **[CLEAN_ARCHITECTURE_MIGRATION.md](docs/CLEAN_ARCHITECTURE_MIGRATION.md)**: Migration progress
- **[DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md)**: Development workflows
- **[TESTING_GUIDE.md](docs/TESTING_GUIDE.md)**: Testing strategies

### Database & Domain
- **[DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)**: Database structure
- **[DOMAIN_MODEL.md](docs/DOMAIN_MODEL.md)**: Business entities
- **[USE_CASES.md](docs/USE_CASES.md)**: Application workflows

### Operations
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)**: Deployment procedures
- **[MONITORING.md](docs/MONITORING.md)**: Monitoring setup

## Important Notes

### Critical Requirements
- **API Key Required**: `GOOGLE_API_KEY` must be set in `.env` for Gemini API access
- **Processing Order**: Always run `process-minutes → extract-speakers → update-speakers` in sequence
- **GCS Authentication**: Run `gcloud auth application-default login` before using GCS features

### File Management
- **Intermediate Files**: Always create temporary files in `tmp/` directory (gitignored)
- **Knowledge Base**: Record important decisions in `_docs/` (gitignored, for Claude's memory)

### Code Quality
- **Pre-commit Hooks**: **NEVER use `--no-verify`** - always fix errors before committing
- **Testing**: External services (LLM, APIs) must be mocked in tests
- **CI/CD**: Create Issues for any skipped tests with `continue-on-error: true`

### Database
- **Master Data**: Governing bodies and conferences are fixed master data
- **Coverage**: All 1,966 Japanese municipalities tracked with organization codes
- **Migrations**: Always add new migrations to `database/02_run_migrations.sql`

### Development
- **Docker-first**: All commands run through Docker containers
- **Unified CLI**: `polibase` command provides single entry point
- **GCS URI Format**: Always use `gs://` format, not HTTPS URLs

**📖 For detailed conventions**: See [.claude/skills/project-conventions/](.claude/skills/project-conventions/)
