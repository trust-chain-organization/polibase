---
name: test-writer
description: Guides test creation for Polibase following strict testing standards. Activates when writing tests or creating test files. Enforces external service mocking (no real API calls), async/await patterns, test independence, and proper use of pytest-asyncio to prevent CI failures and API costs.
---

# Test Writer

## Purpose
Guide test creation following Polibase testing standards with proper mocking, async/await patterns, and independence from external services.

## When to Activate
This skill activates automatically when:
- Writing new tests
- Creating test files in `tests/` directory
- User mentions "test", "pytest", or "testing"
- Reviewing existing test code

## 🚫 CRITICAL: Never Call External Services

**ABSOLUTELY FORBIDDEN in tests:**
- ❌ Real API calls to Google Gemini or any LLM
- ❌ Actual HTTP requests to external websites
- ❌ Real database connections (except integration tests)
- ❌ File system operations outside temp directories
- ❌ Network connections of any kind

**Why?**
- Tests must run in CI/CD without API keys
- Tests must be fast (< 1 second per test)
- Tests must be deterministic (same result every time)
- Tests must not incur API costs

## Quick Checklist

Before committing tests:

- [ ] **No External Calls**: All external services mocked
- [ ] **Fast Execution**: Each test runs in < 1 second
- [ ] **Isolated**: Tests don't depend on each other
- [ ] **Deterministic**: Same result every time
- [ ] **Clear Names**: Test name describes what it tests
- [ ] **Arrange-Act-Assert**: Clear test structure
- [ ] **Async Properly**: Uses `@pytest.mark.asyncio` and `AsyncMock`
- [ ] **Mock Verification**: Asserts mock calls when relevant
- [ ] **Type Hints**: Complete type annotations

## Test Structure

```
tests/
├── unit/              # Fast, isolated tests
│   ├── domain/       # Domain entities and services
│   ├── application/  # Use cases (with mocks)
│   └── infrastructure/  # External services (with mocks)
├── integration/       # Tests with real database
├── evaluation/       # LLM evaluation (manual only, not in CI)
└── conftest.py       # Shared fixtures
```

## Core Testing Patterns

### 1. Mocking External Services

**Always mock:**
```python
from unittest.mock import AsyncMock

@pytest.fixture
def mock_llm_service():
    mock = AsyncMock(spec=ILLMService)
    mock.generate_text.return_value = "Mocked response"
    return mock
```

### 2. Async Tests

**Use pytest-asyncio:**
```python
@pytest.mark.asyncio
async def test_async_function(mock_repo):
    result = await usecase.execute(input_dto)
    assert result.success
```

### 3. Test Independence

**Each test is self-contained:**
```python
def test_create_politician(mock_repo):
    # Setup mock
    mock_repo.save.return_value = Politician(id=1, name="Test")

    # Execute
    result = usecase.execute(input_dto)

    # Assert
    assert result.success
```

## Templates

Use templates in `templates/` directory for:
- Domain service tests
- Use case tests with mocks
- Repository integration tests
- External service tests with mocks

## Detailed Reference

For comprehensive testing patterns, mocking strategies, and best practices, see [reference.md](reference.md).

## Examples

See [examples.md](examples.md) for concrete test examples at each layer.

## Running Tests

```bash
# Run all tests
docker compose -f docker/docker-compose.yml [-f docker/docker-compose.override.yml] exec polibase uv run pytest

# Run specific test file
docker compose -f docker/docker-compose.yml [-f docker/docker-compose.override.yml] exec polibase uv run pytest tests/unit/domain/test_speaker_domain_service.py

# Run with coverage
docker compose -f docker/docker-compose.yml [-f docker/docker-compose.override.yml] exec polibase uv run pytest --cov=src

# Run only unit tests
docker compose -f docker/docker-compose.yml [-f docker/docker-compose.override.yml] exec polibase uv run pytest tests/unit/
```

## Common Anti-Patterns

1. **❌ Real API Calls**: Most common mistake!
2. **❌ Testing Implementation Details**: Test public interfaces
3. **❌ Test Dependencies**: Each test must be independent
4. **❌ Missing Async/Await**: Forget `@pytest.mark.asyncio`
5. **❌ No Mock Verification**: Don't check if mocks were called

See [reference.md](reference.md) for detailed explanations and fixes.
