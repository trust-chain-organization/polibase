# Polibase Tech Stack

## Core Technologies
- **Language**: Python 3.11+ (3.13 in Docker environment)
- **Package Manager**: UV (modern Python package manager)
- **Database**: PostgreSQL 15 with SQLAlchemy ORM
- **Container**: Docker & Docker Compose
- **Task Runner**: Just command runner

## LLM & AI
- **LLM API**: Google Gemini API
  - gemini-2.0-flash (primary)
  - gemini-1.5-flash (fallback)
- **LLM Framework**: LangChain for LLM integration
- **State Management**: LangGraph for complex workflows
- **Prompt Management**: Versioned prompts (開発中)

## Web Technologies
- **UI Framework**: Streamlit for web interface
- **Web Scraping**:
  - Playwright (primary, JavaScript-heavy sites)
  - BeautifulSoup4 (HTML parsing)
  - Selenium (legacy)
- **API Framework**: FastAPI with Uvicorn
- **Async**: aiohttp, asyncio

## Data Processing
- **PDF Processing**: pypdfium2
- **Data Manipulation**: Pandas, NumPy
- **JSON**: orjson for performance
- **Validation**: Pydantic for data models

## Cloud & Storage
- **Cloud Storage**: Google Cloud Storage (GCS)
- **GCS Auth**: gcloud CLI
- **Storage Pattern**: Date-based organization

## Data Visualization
- **Interactive Charts**: Plotly
- **Map Visualization**: Folium (Japan maps)
- **Streamlit Integration**: streamlit-folium
- **Dashboard**: Streamlit-based monitoring

## Development Tools
- **Code Formatter**: Ruff
  - Line length: 88 characters
  - Import sorting enabled
- **Type Checker**: Pyright
  - Python 3.11+ type hints
  - Standard mode
- **Pre-commit Hooks**:
  - Ruff (Python)
  - Prettier (YAML/JSON)
  - Standard hooks
- **Testing**:
  - pytest with fixtures
  - pytest-asyncio for async tests
  - pytest-cov for coverage
  - pytest-mock for mocking

## Monitoring & Logging
- **Logging**: structlog for structured logging
- **Monitoring**: OpenTelemetry
- **Metrics**: Prometheus
- **Visualization**: Grafana
- **Log Aggregation**: Loki
- **Error Tracking**: Sentry SDK

## Architecture Patterns
- **Clean Architecture**: Domain-driven design
- **Repository Pattern**: Data access abstraction
- **Dependency Injection**: Use case composition
- **DTO Pattern**: Layer separation
- **Async/Await**: Throughout the application
- **Staging Tables**: For data review workflows

## CI/CD
- **CI Platform**: GitHub Actions
- **Workflows**:
  - Test on push/PR
  - Ruff formatting check
  - Pyright type checking
  - pytest execution
- **Docker Build**: Multi-stage builds

## MCP Servers (Claude Code Integration)
- **Playwright MCP**: Browser automation for testing
- **Serena MCP**: Code intelligence and semantic operations
- **Context7 MCP**: Library documentation retrieval

## Database Technologies
- **ORM**: SQLAlchemy 2.0+
- **Migrations**: Sequential SQL files
- **Connection Pool**: SQLAlchemy pool
- **Async DB**: asyncpg (planned)

## Environment Management
- **Config**: Environment variables (.env)
- **Secrets**: Never committed, use .env.example
- **Docker Networking**: Custom networks
- **Port Management**: docker-compose.override.yml for git worktree

## Current Development Focus
- LLM処理履歴記録システム
- プロンプトバージョン管理
- インstrumentedLLMService (デコレータパターン)
- Clean Architecture完全移行
