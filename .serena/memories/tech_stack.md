# Polibase Tech Stack

## Core Technologies
- **Language**: Python 3.13
- **Package Manager**: UV (modern Python package manager)
- **Database**: PostgreSQL 15 with SQLAlchemy ORM
- **Container**: Docker & Docker Compose

## Frameworks & Libraries
- **LLM**: Google Gemini API (gemini-2.0-flash, gemini-1.5-flash) via LangChain
- **State Management**: LangGraph for complex workflows
- **Web Framework**: Streamlit for UI
- **API Framework**: FastAPI with Uvicorn
- **PDF Processing**: pypdfium2
- **Web Scraping**: Playwright, BeautifulSoup4, Selenium
- **Async**: aiohttp, asyncio
- **Cloud Storage**: Google Cloud Storage

## Data Visualization
- Plotly for interactive charts
- Folium for Japan map visualization
- Streamlit-folium for map integration
- Pandas for data manipulation

## Development Tools
- **Code Formatter**: Ruff (line length: 88)
- **Type Checker**: Pyright (Python 3.13, standard mode)
- **Pre-commit Hooks**: Ruff, Pyright, Prettier (YAML/JSON)
- **Testing**: pytest with pytest-asyncio, pytest-cov, pytest-mock
- **Logging**: structlog
- **Monitoring**: OpenTelemetry, Prometheus, Grafana, Loki
- **Error Tracking**: Sentry SDK

## Architecture
- Transitioning to Clean Architecture
- Domain-driven design with entities, repositories, use cases
- Repository pattern for data access
- Dependency injection in use cases
- DTOs for layer separation
- Async/await throughout

## MCP Servers
- Playwright MCP for UI testing
- Serena MCP for code intelligence and semantic operations
