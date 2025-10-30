# Clean Architecture Reference

This document provides detailed reference information for implementing Clean Architecture in Polibase.

## Layer Structure

### Domain Layer (`src/domain/`)

**Purpose**: Core business logic and rules

**Contains**:
- **Entities** (21 files): Business objects with identity
  - `BaseEntity`: Common fields (`id`, `created_at`, `updated_at`)
  - Business entities: `Politician`, `Speaker`, `Meeting`, etc.
- **Repository Interfaces** (22 files): Abstract data access
  - `BaseRepository[T]`: Generic CRUD operations
  - `ISessionAdapter`: Database session abstraction
  - Entity-specific methods
- **Domain Services** (18 files): Business logic not belonging to entities
  - `SpeakerDomainService`: Name normalization, similarity
  - `PoliticianDomainService`: Deduplication, validation
  - `MinutesDomainService`: Text processing
- **Service Interfaces** (8 files): External service abstractions
  - `ILLMService`, `IStorageService`, `IWebScraperService`

**Rules**:
- ✅ No imports from outer layers
- ✅ Framework-independent (no SQLAlchemy, no Streamlit)
- ✅ Only Python standard library and minimal dependencies
- ✅ All repository interfaces use `async def`

### Application Layer (`src/application/`)

**Purpose**: Application-specific business rules and orchestration

**Contains**:
- **Use Cases** (21 files): Application workflows
  - Coordinate between repositories and services
  - Transaction boundaries
  - Error handling
- **DTOs** (16 files): Data Transfer Objects
  - Input DTOs: Request data
  - Output DTOs: Response data
  - Validation logic

**Rules**:
- ✅ Import only from Domain layer
- ✅ Use repository interfaces (not implementations)
- ✅ Accept and return DTOs (not entities)
- ✅ No direct database access
- ✅ No UI concerns

### Infrastructure Layer (`src/infrastructure/`)

**Purpose**: External service implementations and technical details

**Contains**:
- **Persistence** (22+ files): Database implementations
  - `BaseRepositoryImpl[T]`: Generic SQLAlchemy repository
  - Entity-specific repository implementations
  - `AsyncSessionAdapter`: Session adapter
  - `UnitOfWorkImpl`: Transaction management
- **External Services**: Third-party integrations
  - `GeminiLLMService`: Google Gemini API
  - `CachedLLMService`: Decorator for caching
  - `InstrumentedLLMService`: Decorator for instrumentation
  - `GCSStorageService`: Google Cloud Storage
  - `WebScraperService`: Playwright-based scraping
- **Infrastructure Support**:
  - DI Container (`di/`): Dependency injection
  - Logging, monitoring, error handling

**Rules**:
- ✅ Import from Domain and Application
- ✅ Implement interfaces defined in Domain
- ✅ All repository methods are `async def`
- ✅ Use `ISessionAdapter` for database operations
- ✅ Convert between domain entities and SQLAlchemy models

### Interfaces Layer (`src/interfaces/`)

**Purpose**: User interface and external API adapters

**Contains**:
- **CLI** (`src/interfaces/cli/`): Command-line interfaces
  - Unified `polibase` command
  - Command groups: `scraping/`, `database/`, `processing/`
- **Web** (`src/interfaces/web/streamlit/`): Web UI
  - `views/`: Page views
  - `presenters/`: Business logic presentation
  - `components/`: Reusable UI components
  - `dto/`: UI-specific DTOs

**Rules**:
- ✅ Import from all inner layers
- ✅ Use use cases (not repositories directly)
- ✅ Convert between UI format and DTOs
- ✅ No business logic (delegate to use cases)
- ❌ No imports between different Interface modules

## Repository Pattern Details

### Interface Definition (Domain)

```python
# src/domain/repositories/politician_repository.py
from typing import Protocol
from src.domain.entities.politician import Politician
from src.domain.repositories.base_repository import BaseRepository

class IPoliticianRepository(BaseRepository[Politician]):
    """Repository interface for Politician entities."""

    async def find_by_name(self, name: str) -> list[Politician]:
        """Find politicians by exact name match."""
        ...

    async def find_by_party(self, party_id: int) -> list[Politician]:
        """Find all politicians belonging to a party."""
        ...

    async def search_by_name_fuzzy(
        self, name: str, threshold: float = 0.8
    ) -> list[tuple[Politician, float]]:
        """Fuzzy search politicians by name with similarity scores."""
        ...
```

### Implementation (Infrastructure)

```python
# src/infrastructure/persistence/politician_repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.entities.politician import Politician
from src.domain.repositories.politician_repository import IPoliticianRepository
from src.infrastructure.persistence.base_repository import BaseRepositoryImpl
from src.infrastructure.persistence.models.politician import Politician as PoliticianModel

class PoliticianRepositoryImpl(
    BaseRepositoryImpl[Politician], IPoliticianRepository
):
    """SQLAlchemy implementation of IPoliticianRepository."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, PoliticianModel, Politician)

    async def find_by_name(self, name: str) -> list[Politician]:
        query = select(PoliticianModel).where(PoliticianModel.name == name)
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def find_by_party(self, party_id: int) -> list[Politician]:
        query = select(PoliticianModel).where(
            PoliticianModel.party_id == party_id
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    def _to_entity(self, model: PoliticianModel) -> Politician:
        """Convert SQLAlchemy model to domain entity."""
        return Politician(
            id=model.id,
            name=model.name,
            party_id=model.party_id,
            furigana=model.furigana,
            # ... other fields
        )

    def _to_model(self, entity: Politician) -> PoliticianModel:
        """Convert domain entity to SQLAlchemy model."""
        return PoliticianModel(
            id=entity.id,
            name=entity.name,
            party_id=entity.party_id,
            furigana=entity.furigana,
            # ... other fields
        )
```

## Use Case Pattern Details

### Use Case Structure

```python
# src/application/usecases/create_politician_usecase.py
from src.application.dto.politician_dto import (
    CreatePoliticianInputDTO,
    CreatePoliticianOutputDTO,
)
from src.domain.repositories.politician_repository import IPoliticianRepository
from src.domain.repositories.political_party_repository import IPoliticalPartyRepository
from src.domain.services.politician_domain_service import PoliticianDomainService
from src.domain.entities.politician import Politician

class CreatePoliticianUseCase:
    """Use case for creating a new politician."""

    def __init__(
        self,
        politician_repository: IPoliticianRepository,
        party_repository: IPoliticalPartyRepository,
        politician_service: PoliticianDomainService,
    ):
        self.politician_repository = politician_repository
        self.party_repository = party_repository
        self.politician_service = politician_service

    async def execute(
        self, input_dto: CreatePoliticianInputDTO
    ) -> CreatePoliticianOutputDTO:
        """
        Execute the use case.

        Args:
            input_dto: Input data for creating a politician

        Returns:
            Output DTO with result information

        Raises:
            ValueError: If party doesn't exist or data is invalid
        """
        # Validate party exists
        party = await self.party_repository.find_by_id(input_dto.party_id)
        if party is None:
            raise ValueError(f"Party with id {input_dto.party_id} not found")

        # Check for duplicates using domain service
        existing = await self.politician_repository.find_by_name(input_dto.name)
        if self.politician_service.has_duplicate(input_dto.name, existing):
            raise ValueError(f"Politician {input_dto.name} already exists")

        # Create entity
        politician = Politician(
            id=None,  # Will be assigned by database
            name=input_dto.name,
            party_id=input_dto.party_id,
            furigana=input_dto.furigana,
        )

        # Save to repository
        saved_politician = await self.politician_repository.save(politician)

        # Return output DTO
        return CreatePoliticianOutputDTO(
            success=True,
            politician_id=saved_politician.id,
            message=f"Successfully created politician: {saved_politician.name}",
        )
```

## Domain Service vs Entity

### When to Use Domain Services

Use domain services when:
- Logic involves multiple entities
- Logic doesn't naturally belong to any single entity
- Logic requires external dependencies (repositories, etc.)
- Logic is a pure algorithm or calculation

### When to Use Entity Methods

Use entity methods when:
- Logic operates on single entity's data
- Logic is intrinsic to the entity's identity
- Logic doesn't require external dependencies
- Logic is simple state change or validation

### Example: Speaker Name Normalization

**Domain Service** (correct placement):
```python
# src/domain/services/speaker_domain_service.py
class SpeakerDomainService:
    """Domain service for speaker-related business logic."""

    HONORIFICS = ["氏", "君", "議員", "委員", "さん"]

    def normalize_name(self, raw_name: str) -> str:
        """
        Normalize speaker name by removing honorifics and standardizing format.

        Args:
            raw_name: Raw name from minutes

        Returns:
            Normalized name
        """
        name = raw_name.strip()
        name = name.replace("　", " ")  # Full-width to half-width space

        # Remove honorifics
        for honorific in self.HONORIFICS:
            if name.endswith(honorific):
                name = name[: -len(honorific)]

        return name.strip()

    def calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity score between two names."""
        # Levenshtein distance or other algorithm
        ...
```

**Why Service?** Name normalization is a pure algorithm that doesn't depend on any specific Speaker entity's state.

## DTO Pattern Details

### Input DTO

```python
# src/application/dto/politician_dto.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class CreatePoliticianInputDTO:
    """Input data for creating a politician."""

    name: str
    party_id: int
    furigana: Optional[str] = None
    district: Optional[str] = None

    def validate(self) -> None:
        """Validate input data."""
        if not self.name or not self.name.strip():
            raise ValueError("Name is required")
        if self.party_id <= 0:
            raise ValueError("Invalid party_id")
        if len(self.name) > 100:
            raise ValueError("Name too long (max 100 characters)")
```

### Output DTO

```python
@dataclass
class CreatePoliticianOutputDTO:
    """Output data from creating a politician."""

    success: bool
    politician_id: Optional[int] = None
    message: str = ""
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
```

### Why DTOs?

1. **Stability**: Domain entities can change without breaking interfaces
2. **Validation**: DTOs can have validation logic separate from entities
3. **Transformation**: Convert between different representations
4. **Security**: Don't expose internal entity structure
5. **Versioning**: Different DTO versions for API versioning

## Async/Await Pattern

All repository methods MUST be async:

```python
# ✅ CORRECT
async def find_by_id(self, id: int) -> Politician | None:
    result = await self.session.execute(
        select(PoliticianModel).where(PoliticianModel.id == id)
    )
    model = result.scalar_one_or_none()
    return self._to_entity(model) if model else None

# ❌ WRONG: Synchronous method
def find_by_id(self, id: int) -> Politician | None:
    result = self.session.execute(...)  # Missing await!
```

Use cases must also be async:

```python
# ✅ CORRECT
async def execute(self, input_dto: InputDTO) -> OutputDTO:
    entity = await self.repository.find_by_id(input_dto.id)
    # ...

# ❌ WRONG: Synchronous use case
def execute(self, input_dto: InputDTO) -> OutputDTO:
    entity = self.repository.find_by_id(input_dto.id)  # Won't work!
```

## Type Safety Guidelines

### Use Union Types

```python
# ✅ CORRECT (Python 3.10+)
def find_politician(id: int) -> Politician | None:
    ...

# ✅ CORRECT (older style)
from typing import Optional
def find_politician(id: int) -> Optional[Politician]:
    ...
```

### Explicit None Checks

```python
# ✅ CORRECT
politician = await repository.find_by_id(1)
if politician is not None:
    print(politician.name)  # Type checker knows it's not None
else:
    raise ValueError("Not found")

# ❌ WRONG
politician = await repository.find_by_id(1)
print(politician.name)  # Type error: might be None
```

### Generic Type Parameters

```python
# ✅ CORRECT
class BaseRepository(Protocol[T]):
    async def find_by_id(self, id: int) -> T | None:
        ...

class PoliticianRepository(BaseRepository[Politician]):
    pass  # Inherits correct return types
```

## Testing Strategy

### Unit Tests for Domain Services

```python
# tests/unit/domain/test_speaker_domain_service.py
def test_normalize_name_removes_honorifics():
    service = SpeakerDomainService()
    assert service.normalize_name("山田太郎氏") == "山田太郎"
```

### Unit Tests for Use Cases (with mocks)

```python
# tests/unit/application/test_create_politician_usecase.py
@pytest.mark.asyncio
async def test_execute_creates_politician(mock_repo):
    mock_repo.save.return_value = Politician(id=1, name="Test")
    usecase = CreatePoliticianUseCase(mock_repo)
    output = await usecase.execute(input_dto)
    assert output.success
```

### Integration Tests for Repositories

```python
# tests/integration/test_politician_repository.py
@pytest.mark.asyncio
async def test_find_by_id_returns_politician(db_session):
    repo = PoliticianRepositoryImpl(db_session)
    politician = await repo.find_by_id(1)
    assert politician is not None
```

## Migration Checklist

When migrating existing code to Clean Architecture:

1. [ ] Create domain entity (if doesn't exist)
2. [ ] Create repository interface in Domain
3. [ ] Create repository implementation in Infrastructure
4. [ ] Create DTOs in Application
5. [ ] Create use case in Application
6. [ ] Update interface layer (CLI/Web) to use use case
7. [ ] Write unit tests for domain services
8. [ ] Write unit tests for use cases (with mocks)
9. [ ] Write integration tests for repositories
10. [ ] Remove old direct database access code
11. [ ] Update documentation

## Common Pitfalls

### Pitfall 1: Domain Entities with Framework Dependencies

```python
# ❌ BAD: SQLAlchemy in domain
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Politician(Base):
    __tablename__ = 'politicians'
    id = Column(Integer, primary_key=True)
    name = Column(String)
```

**Fix**: Keep entities pure, SQLAlchemy models in Infrastructure

### Pitfall 2: Use Cases Containing Business Logic

```python
# ❌ BAD: Business logic in use case
class ProcessMinutesUseCase:
    async def execute(self, input_dto):
        # Complex name normalization here
        name = input_dto.name.strip().replace("　", " ")
        for honorific in ["氏", "君"]:
            if name.endswith(honorific):
                name = name[:-len(honorific)]
        # More logic...
```

**Fix**: Move to domain service

### Pitfall 3: Repositories Returning DTOs

```python
# ❌ BAD: Repository returns DTO
class PoliticianRepositoryImpl:
    async def find_by_id(self, id: int) -> PoliticianOutputDTO:
        # Returns DTO instead of entity
```

**Fix**: Repositories return domain entities, use cases convert to DTOs

### Pitfall 4: Missing Async/Await

```python
# ❌ BAD: Forgot async/await
class UseCase:
    def execute(self, input_dto):
        result = self.repository.find_by_id(1)  # Missing await
```

**Fix**: Make everything async

## Further Reading

- [CLEAN_ARCHITECTURE_MIGRATION.md](../../../docs/CLEAN_ARCHITECTURE_MIGRATION.md) - Migration guide
- [tmp/clean_architecture_analysis_2025.md](../../../tmp/clean_architecture_analysis_2025.md) - Detailed analysis
- Robert C. Martin's "Clean Architecture" book
- Hexagonal Architecture by Alistair Cockburn
