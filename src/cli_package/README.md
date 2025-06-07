# CLI Package Structure

This package contains the refactored CLI implementation for Polibase, organized for better maintainability and modularity.

## Structure

```
cli_package/
├── __init__.py          # Package exports
├── base.py              # Base command class and decorators
├── utils.py             # Shared utilities
└── commands/            # Command modules
    ├── __init__.py
    ├── database_commands.py   # Database management commands
    ├── minutes_commands.py    # Meeting minutes processing commands
    ├── politician_commands.py # Politician data processing commands
    ├── scraping_commands.py   # Web scraping commands
    └── ui_commands.py        # User interface commands
```

## Key Features

### Base Command Class
- `BaseCommand`: Provides common functionality for all commands
- Decorators: `@with_error_handling`, `@with_async_execution`
- Utility methods: `show_progress()`, `success()`, `error()`, `confirm()`

### Command Organization
- **Database Commands**: `test-connection`, `database`, `reset-database`
- **Minutes Commands**: `process-minutes`, `update-speakers`
- **Politician Commands**: `extract-politicians`, `scrape-politicians`
- **Scraping Commands**: `scrape-minutes`, `batch-scrape`
- **UI Commands**: `streamlit`

### Utilities
- `ProgressTracker`: Display progress for long operations
- `AsyncRunner`: Execute async operations in sync context
- `ensure_directory()`: Create directories as needed
- `setup_gcs_environment()`: Configure Google Cloud Storage

## Usage

The main CLI entry point (`src/cli.py`) imports and registers all commands from this package:

```python
from src.cli_package.commands import (
    get_minutes_commands,
    get_scraping_commands,
    get_politician_commands,
    get_ui_commands,
    get_database_commands
)
```

Each command module exports a function that returns a list of Click commands, making it easy to add or remove commands modularly.
