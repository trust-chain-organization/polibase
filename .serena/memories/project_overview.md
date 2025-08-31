# Polibase Project Overview

Polibase (政治活動追跡アプリケーション) is a Political Activity Tracking Application for managing and analyzing Japanese political activities including politician statements, meeting minutes, political promises, and voting records.

## Main Purpose
- Extract and structure political discussions from meeting minutes (PDFs and web pages)
- Track politicians, their affiliations, and statements
- Link speakers in meetings to politicians using LLM-based matching
- Monitor data coverage across Japanese governmental bodies
- Manage parliamentary groups (議員団/会派) and their voting patterns
- **Track LLM processing history for reproducibility and transparency**

## Key Features
1. **Minutes Processing**: Extract speeches from meeting PDFs/text with LangGraph
2. **Politician Management**: Scrape and maintain politician data from party websites
3. **Speaker Matching**: LLM-powered linking of speakers to politicians
4. **Conference Member Extraction**: Staged extraction and matching of conference members
5. **Parliamentary Groups**: Track voting blocs within conferences
6. **Data Coverage Monitoring**: Visualize data completeness across Japan
7. **Web UI**: Streamlit-based interface for data management
8. **LLM History Tracking**: Record all LLM processing for audit trail (開発中)

## System Design Principles
1. Politicians data comes from party websites
2. Speakers and speeches extracted from meeting minutes
3. LLM links speakers to politicians with high accuracy
4. Conference members extracted in stages with manual review
5. Parliamentary groups track voting patterns
6. All data input through Streamlit UI
7. Coverage monitored via dashboards
8. **LLM processing history tracked for reproducibility**
9. **Prompt versioning for consistent results**

## Architecture
- **Clean Architecture**: Domain-driven design with clear layer separation
- **Domain Layer**: Core business logic and entities
- **Application Layer**: Use cases and DTOs
- **Infrastructure Layer**: Database, external services (LLM, storage, scraping)
- **Interfaces Layer**: CLI and Web UI

## Technology Stack
- **Language**: Python 3.11+
- **LLM**: Google Gemini API (gemini-2.0-flash, gemini-1.5-flash)
- **Database**: PostgreSQL 15 with SQLAlchemy ORM
- **Package Manager**: UV (modern Python package manager)
- **Web Scraping**: Playwright, BeautifulSoup4
- **State Management**: LangGraph for complex workflows
- **Cloud Storage**: Google Cloud Storage (GCS)
- **UI**: Streamlit for web interface
- **Visualization**: Plotly, Folium for maps
- **CI/CD**: GitHub Actions
- **Container**: Docker with docker-compose

## Database
- PostgreSQL 15 with SQLAlchemy ORM
- Master data: governing_bodies (1,966 municipalities), conferences, political_parties
- Core tables: meetings, minutes, speakers, politicians, conversations, proposals
- Staging tables for review: extracted_conference_members
- Parliamentary groups: parliamentary_groups, parliamentary_group_memberships
- **LLM tracking**: llm_processing_history, prompt_versions (計画中)
- Comprehensive migration system in database/migrations/

## Development Workflow
1. **Docker-first**: All commands run through docker compose
2. **Just commands**: Simplified task runner for common operations
3. **Clean Architecture**: Strict layer separation
4. **Type Safety**: Python type hints with pyright
5. **Code Quality**: Ruff for formatting and linting
6. **Pre-commit hooks**: Automatic code quality checks
7. **Testing**: pytest with async support

## Current Development Focus
- LLM処理履歴記録システムの実装 (#128)
- プロンプトバージョン管理機能
- 処理トレーサビリティの向上
- Clean Architecture移行の完了 (Phase 3)
