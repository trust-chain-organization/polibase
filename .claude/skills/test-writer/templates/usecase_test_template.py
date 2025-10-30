"""
Template for testing use cases with mocks.

Replace:
- UseCaseName: Your use case name
- OperationName: Your operation (e.g., CreatePolitician)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dto.operation_dto import (
    OperationNameInputDTO,
)
from src.application.usecases.usecase_name import UseCaseName
from src.domain.entities.entity_name import EntityName


class TestUseCaseName:
    """Test suite for UseCaseName use case."""

    @pytest.fixture
    def mock_entity_repo(self):
        """Mock entity repository."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def mock_service(self):
        """Mock domain service."""
        mock = MagicMock()
        return mock

    @pytest.fixture
    def usecase(self, mock_entity_repo, mock_service):
        """Create use case with mocked dependencies."""
        return UseCaseName(
            entity_repository=mock_entity_repo,
            entity_service=mock_service,
        )

    # Happy path test
    @pytest.mark.asyncio
    async def test_execute_succeeds_with_valid_input(
        self, usecase, mock_entity_repo, mock_service
    ):
        """Test use case succeeds with valid input."""
        # Arrange
        input_dto = OperationNameInputDTO(
            name="Test",
            # Add other input fields
        )
        mock_entity_repo.save.return_value = EntityName(
            id=1,
            name="Test",
        )

        # Act
        output_dto = await usecase.execute(input_dto)

        # Assert
        assert output_dto.success is True
        assert output_dto.entity_id == 1
        mock_entity_repo.save.assert_called_once()

    # Validation error test
    @pytest.mark.asyncio
    async def test_execute_fails_with_invalid_input(self, usecase):
        """Test use case fails with invalid input."""
        # Arrange
        input_dto = OperationNameInputDTO(
            name="",  # Invalid: empty name
        )

        # Act
        output_dto = await usecase.execute(input_dto)

        # Assert
        assert output_dto.success is False
        assert "Name is required" in output_dto.message

    # Business rule violation test
    @pytest.mark.asyncio
    async def test_execute_fails_when_entity_already_exists(
        self, usecase, mock_entity_repo
    ):
        """Test use case fails when entity already exists."""
        # Arrange
        input_dto = OperationNameInputDTO(name="Existing")
        mock_entity_repo.find_by_name.return_value = [EntityName(id=1, name="Existing")]

        # Act & Assert
        with pytest.raises(ValueError, match="already exists"):
            await usecase.execute(input_dto)

    # Dependency not found test
    @pytest.mark.asyncio
    async def test_execute_fails_when_dependency_not_found(
        self, usecase, mock_entity_repo
    ):
        """Test use case fails when required dependency not found."""
        # Arrange
        input_dto = OperationNameInputDTO(
            name="Test",
            parent_id=999,  # Non-existent parent
        )
        mock_entity_repo.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="not found"):
            await usecase.execute(input_dto)

    # Domain service interaction test
    @pytest.mark.asyncio
    async def test_execute_calls_domain_service(
        self, usecase, mock_service, mock_entity_repo
    ):
        """Test use case delegates to domain service."""
        # Arrange
        input_dto = OperationNameInputDTO(name="Test")
        mock_service.process.return_value = "processed_value"
        mock_entity_repo.save.return_value = EntityName(id=1, name="Test")

        # Act
        await usecase.execute(input_dto)

        # Assert
        mock_service.process.assert_called_once()

    # Error handling test
    @pytest.mark.asyncio
    async def test_execute_handles_repository_error(self, usecase, mock_entity_repo):
        """Test use case handles repository errors gracefully."""
        # Arrange
        input_dto = OperationNameInputDTO(name="Test")
        mock_entity_repo.save.side_effect = Exception("Database error")

        # Act
        output_dto = await usecase.execute(input_dto)

        # Assert
        assert output_dto.success is False
        assert "error" in output_dto.message.lower()

    # Multiple entities test
    @pytest.mark.asyncio
    async def test_execute_processes_multiple_entities(self, usecase, mock_entity_repo):
        """Test use case can process multiple entities."""
        # Arrange
        input_dto = OperationNameInputDTO(entity_ids=[1, 2, 3])
        mock_entity_repo.find_by_id.side_effect = [
            EntityName(id=1, name="Entity1"),
            EntityName(id=2, name="Entity2"),
            EntityName(id=3, name="Entity3"),
        ]

        # Act
        output_dto = await usecase.execute(input_dto)

        # Assert
        assert output_dto.success is True
        assert output_dto.processed_count == 3
        assert mock_entity_repo.find_by_id.call_count == 3
