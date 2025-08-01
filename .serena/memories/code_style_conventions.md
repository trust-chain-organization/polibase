# Polibase Code Style and Conventions

## Python Style
- **Python Version**: 3.13 (requires ~=3.13.0)
- **Line Length**: 88 characters (Ruff default)
- **Import Style**: Sorted by isort rules, with src as first-party
- **Type Hints**: Required throughout, using Python 3.11+ features
- **Docstrings**: Google style for classes and methods

## Naming Conventions
- **Files**: snake_case (e.g., `speaker_repository.py`)
- **Classes**: PascalCase (e.g., `SpeakerRepository`)
- **Functions/Methods**: snake_case (e.g., `get_by_name_party_position`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DATABASE_URL`)
- **Private**: Leading underscore (e.g., `_extract_speeches`)

## Project Structure
- **src/domain/**: Entities, repository interfaces, domain services
- **src/application/**: Use cases, DTOs
- **src/infrastructure/**: Repository implementations, external services
- **src/interfaces/**: CLI, Web UI
- **src/database/**: Legacy database layer (being migrated)
- **src/common/**: Shared utilities
- **tests/**: Mirror src structure

## Clean Architecture Rules
- Dependencies point inward: Domain ← Application ← Infrastructure ← Interfaces
- Domain entities are framework-independent
- Repository interfaces in domain, implementations in infrastructure
- Use cases inject dependencies
- DTOs transfer data between layers
- All repository methods are async

## Type Safety
- Explicit None checks for Optional types
- Type narrowing for string operations
- Generic types with TypeVar
- Protocol classes for interfaces
- Pyright in standard mode

## Async Patterns
- All repository methods use async/await
- Async context managers for database sessions
- AsyncRunner utility for CLI commands
- pytest-asyncio for async tests

## Error Handling
- Custom exception hierarchy in src/exceptions.py
- Domain-specific exceptions (e.g., `RecordNotFoundError`)
- Proper error propagation through layers
- Sentry integration for production

## Comments
- **IMPORTANT**: DO NOT ADD ANY COMMENTS unless explicitly asked
- Code should be self-documenting through clear naming
- Docstrings only where necessary for public APIs
