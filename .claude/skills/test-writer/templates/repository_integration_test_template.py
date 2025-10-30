"""
Template for integration testing repositories with real database.

Replace:
- RepositoryName: Your repository name
- EntityName: Your entity name
"""

import pytest

from src.domain.entities.entity_name import EntityName
from src.infrastructure.persistence.repository_name import RepositoryNameImpl


@pytest.mark.integration
class TestRepositoryNameIntegration:
    """
    Integration tests for RepositoryName.

    These tests use a real test database and are slower than unit tests.
    Mark with @pytest.mark.integration to run separately.
    """

    @pytest.fixture
    async def repository(self, db_session):
        """
        Create repository with test database session.

        db_session fixture should be defined in conftest.py.
        """
        return RepositoryNameImpl(session=db_session)

    @pytest.fixture
    async def sample_entity(self):
        """Create sample entity for tests."""
        return EntityName(
            id=None,  # Will be assigned by database
            name="Test Entity",
            # Add other fields
        )

    # Basic CRUD tests

    @pytest.mark.asyncio
    async def test_save_persists_entity(self, repository, sample_entity):
        """Test that save persists entity to database."""
        # Act
        saved = await repository.save(sample_entity)

        # Assert
        assert saved.id is not None
        assert saved.name == "Test Entity"

    @pytest.mark.asyncio
    async def test_find_by_id_returns_entity(self, repository, sample_entity):
        """Test find_by_id returns saved entity."""
        # Arrange
        saved = await repository.save(sample_entity)

        # Act
        found = await repository.find_by_id(saved.id)

        # Assert
        assert found is not None
        assert found.id == saved.id
        assert found.name == saved.name

    @pytest.mark.asyncio
    async def test_find_by_id_returns_none_when_not_found(self, repository):
        """Test find_by_id returns None for non-existent ID."""
        # Act
        found = await repository.find_by_id(999999)

        # Assert
        assert found is None

    @pytest.mark.asyncio
    async def test_find_all_returns_all_entities(self, repository):
        """Test find_all returns all persisted entities."""
        # Arrange
        entity1 = EntityName(id=None, name="Entity1")
        entity2 = EntityName(id=None, name="Entity2")
        await repository.save(entity1)
        await repository.save(entity2)

        # Act
        all_entities = await repository.find_all()

        # Assert
        assert len(all_entities) >= 2
        names = [e.name for e in all_entities]
        assert "Entity1" in names
        assert "Entity2" in names

    @pytest.mark.asyncio
    async def test_update_modifies_entity(self, repository, sample_entity):
        """Test updating entity persists changes."""
        # Arrange
        saved = await repository.save(sample_entity)
        saved.name = "Updated Name"

        # Act
        updated = await repository.save(saved)
        found = await repository.find_by_id(updated.id)

        # Assert
        assert found.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_removes_entity(self, repository, sample_entity):
        """Test delete removes entity from database."""
        # Arrange
        saved = await repository.save(sample_entity)

        # Act
        deleted = await repository.delete(saved.id)
        found = await repository.find_by_id(saved.id)

        # Assert
        assert deleted is True
        assert found is None

    # Custom query tests

    @pytest.mark.asyncio
    async def test_find_by_name_returns_matching_entities(self, repository):
        """Test custom query find_by_name returns correct results."""
        # Arrange
        entity1 = EntityName(id=None, name="SearchName")
        entity2 = EntityName(id=None, name="SearchName")
        entity3 = EntityName(id=None, name="DifferentName")
        await repository.save(entity1)
        await repository.save(entity2)
        await repository.save(entity3)

        # Act
        found = await repository.find_by_name("SearchName")

        # Assert
        assert len(found) >= 2
        assert all(e.name == "SearchName" for e in found)

    @pytest.mark.asyncio
    async def test_find_by_name_returns_empty_list_when_not_found(self, repository):
        """Test find_by_name returns empty list for no matches."""
        # Act
        found = await repository.find_by_name("NonExistentName")

        # Assert
        assert found == []

    # Complex query tests

    @pytest.mark.asyncio
    async def test_find_by_criteria_with_multiple_filters(self, repository):
        """Test complex query with multiple filter criteria."""
        # Arrange
        entity1 = EntityName(id=None, name="Test", status="active")
        entity2 = EntityName(id=None, name="Test", status="inactive")
        await repository.save(entity1)
        await repository.save(entity2)

        # Act
        criteria = {"name": "Test", "status": "active"}
        found = await repository.find_by_criteria(criteria)

        # Assert
        assert len(found) >= 1
        assert all(e.name == "Test" and e.status == "active" for e in found)

    # Foreign key tests

    @pytest.mark.asyncio
    async def test_save_with_foreign_key_creates_relationship(
        self, repository, parent_repository
    ):
        """Test saving entity with foreign key creates relationship."""
        # Arrange
        parent = ParentEntity(id=None, name="Parent")
        saved_parent = await parent_repository.save(parent)

        entity = EntityName(id=None, name="Child", parent_id=saved_parent.id)

        # Act
        saved_entity = await repository.save(entity)
        found = await repository.find_by_id(saved_entity.id)

        # Assert
        assert found.parent_id == saved_parent.id

    # Transaction tests

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, repository, db_session):
        """Test transaction rolls back on error."""
        # Arrange
        entity = EntityName(id=None, name="Test")

        try:
            # Act - simulate error during transaction
            await repository.save(entity)
            raise Exception("Simulated error")
        except Exception:
            await db_session.rollback()

        # Assert - entity should not be in database
        all_entities = await repository.find_all()
        assert not any(e.name == "Test" for e in all_entities)

    # Performance tests (optional)

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_bulk_insert_performance(self, repository):
        """Test bulk insert of many entities (marked as slow)."""
        # Arrange
        entities = [EntityName(id=None, name=f"Entity{i}") for i in range(1000)]

        # Act
        for entity in entities:
            await repository.save(entity)

        # Assert
        all_entities = await repository.find_all()
        assert len(all_entities) >= 1000
