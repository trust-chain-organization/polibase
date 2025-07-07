"""Tests for BaseRepositoryImpl."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.base import BaseEntity
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class MockEntity(BaseEntity):
    """Mock entity for testing BaseRepositoryImpl."""

    def __init__(self, id: int | None = None, name: str = ""):
        super().__init__(id=id)
        self.name = name


class MockModel:
    """Mock model for testing BaseRepositoryImpl."""

    def __init__(self, id: int | None = None, name: str = ""):
        self.id = id
        self.name = name


class MockRepositoryImpl(BaseRepositoryImpl[MockEntity]):
    """Test repository implementation."""

    def _to_entity(self, model) -> MockEntity:
        """Convert model to entity."""
        return MockEntity(id=model.id, name=model.name)

    def _to_model(self, entity: MockEntity):
        """Convert entity to model."""
        return MockModel(id=entity.id, name=entity.name)

    def _update_model(self, model, entity: MockEntity):
        """Update model from entity."""
        model.name = entity.name


class TestBaseRepositoryImpl:
    """Test cases for BaseRepositoryImpl."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create test repository."""
        return MockRepositoryImpl(mock_session, MockEntity, MockModel)

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, mock_session):
        """Test get_by_id when entity is found."""
        # Setup
        mock_model = MockModel(id=1, name="Test")
        mock_session.get.return_value = mock_model

        # Execute
        result = await repository.get_by_id(1)

        # Verify
        assert result is not None
        assert result.id == 1
        assert result.name == "Test"
        mock_session.get.assert_called_once_with(MockModel, 1)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_session):
        """Test get_by_id when entity is not found."""
        # Setup
        mock_session.get.return_value = None

        # Execute
        result = await repository.get_by_id(999)

        # Verify
        assert result is None
        mock_session.get.assert_called_once_with(MockModel, 999)

    @pytest.mark.asyncio
    async def test_get_all(self, repository, mock_session):
        """Test get_all method."""
        # Setup
        mock_models = [
            MockModel(id=1, name="Test1"),
            MockModel(id=2, name="Test2"),
        ]
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_models
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_all()

        # Verify
        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].name == "Test1"
        assert result[1].id == 2
        assert result[1].name == "Test2"

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, repository, mock_session):
        """Test get_all with limit and offset."""
        # Setup
        mock_models = [MockModel(id=3, name="Test3")]
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = mock_models
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_all(limit=10, offset=20)

        # Verify
        assert len(result) == 1
        # Check that query was built with limit and offset
        executed_query = mock_session.execute.call_args[0][0]
        assert executed_query is not None

    @pytest.mark.asyncio
    async def test_create(self, repository, mock_session):
        """Test create method."""
        # Setup
        entity = MockEntity(name="New Entity")

        # Mock refresh to update the model with ID
        async def refresh_side_effect(model):
            model.id = 5

        mock_session.refresh.side_effect = refresh_side_effect

        # Execute
        result = await repository.create(entity)

        # Verify
        assert result.id == 5
        assert result.name == "New Entity"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_success(self, repository, mock_session):
        """Test update method with existing entity."""
        # Setup
        entity = MockEntity(id=1, name="Updated Entity")
        existing_model = MockModel(id=1, name="Old Entity")
        mock_session.get.return_value = existing_model

        # Execute
        result = await repository.update(entity)

        # Verify
        assert result.id == 1
        assert result.name == "Updated Entity"
        assert existing_model.name == "Updated Entity"  # Model was updated
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_no_id_error(self, repository):
        """Test update with entity without ID."""
        # Setup
        entity = MockEntity(name="No ID Entity")

        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            await repository.update(entity)

        assert "Entity must have an ID to update" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_not_found_error(self, repository, mock_session):
        """Test update with non-existent entity."""
        # Setup
        entity = MockEntity(id=999, name="Not Found")
        mock_session.get.return_value = None

        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            await repository.update(entity)

        assert "Entity with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_success(self, repository, mock_session):
        """Test delete method with existing entity."""
        # Setup
        model = MockModel(id=1, name="To Delete")
        mock_session.get.return_value = model

        # Execute
        result = await repository.delete(1)

        # Verify
        assert result is True
        mock_session.delete.assert_called_once_with(model)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_session):
        """Test delete with non-existent entity."""
        # Setup
        mock_session.get.return_value = None

        # Execute
        result = await repository.delete(999)

        # Verify
        assert result is False
        mock_session.delete.assert_not_called()
        mock_session.commit.assert_not_called()
