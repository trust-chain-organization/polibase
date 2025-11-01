"""Tests for ManageConferencesUseCase."""

from unittest.mock import AsyncMock, mock_open

import pytest

from src.application.usecases.manage_conferences_usecase import (
    ConferenceListInputDto,
    ConferenceListOutputDto,
    CreateConferenceInputDto,
    CreateConferenceOutputDto,
    DeleteConferenceInputDto,
    DeleteConferenceOutputDto,
    GenerateSeedFileOutputDto,
    ManageConferencesUseCase,
    UpdateConferenceInputDto,
    UpdateConferenceOutputDto,
)
from src.domain.entities.conference import Conference


class TestManageConferencesUseCase:
    """Test cases for ManageConferencesUseCase."""

    @pytest.fixture
    def mock_conference_repository(self):
        """Create mock conference repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def use_case(self, mock_conference_repository):
        """Create ManageConferencesUseCase instance."""
        return ManageConferencesUseCase(
            conference_repository=mock_conference_repository
        )

    @pytest.mark.asyncio
    async def test_list_conferences_success(self, use_case, mock_conference_repository):
        """Test listing conferences successfully."""
        # Arrange
        conferences = [
            Conference(id=1, name="衆議院本会議", governing_body_id=1),
            Conference(id=2, name="参議院本会議", governing_body_id=1),
        ]
        mock_conference_repository.get_all.return_value = conferences

        input_dto = ConferenceListInputDto()

        # Act
        result = await use_case.list_conferences(input_dto)

        # Assert
        assert isinstance(result, ConferenceListOutputDto)
        assert len(result.conferences) == 2
        assert result.conferences[0].name == "衆議院本会議"

    @pytest.mark.asyncio
    async def test_list_conferences_filtered_by_governing_body(
        self, use_case, mock_conference_repository
    ):
        """Test listing conferences filtered by governing body ID."""
        # Arrange
        conferences = [Conference(id=1, name="衆議院本会議", governing_body_id=1)]
        mock_conference_repository.get_by_governing_body.return_value = conferences

        input_dto = ConferenceListInputDto(governing_body_id=1)

        # Act
        result = await use_case.list_conferences(input_dto)

        # Assert
        assert len(result.conferences) == 1
        assert result.conferences[0].governing_body_id == 1

    @pytest.mark.asyncio
    async def test_list_conferences_empty(self, use_case, mock_conference_repository):
        """Test listing conferences when none exist."""
        # Arrange
        mock_conference_repository.get_all.return_value = []

        input_dto = ConferenceListInputDto()

        # Act
        result = await use_case.list_conferences(input_dto)

        # Assert
        assert len(result.conferences) == 0

    @pytest.mark.asyncio
    async def test_create_conference_success(
        self, use_case, mock_conference_repository
    ):
        """Test creating a conference successfully."""
        # Arrange
        mock_conference_repository.get_by_name_and_governing_body.return_value = None
        created_conference = Conference(
            id=1,
            name="東京都議会",
            governing_body_id=13,
        )
        mock_conference_repository.create.return_value = created_conference

        input_dto = CreateConferenceInputDto(
            name="東京都議会",
            governing_body_id=13,
        )

        # Act
        result = await use_case.create_conference(input_dto)

        # Assert
        assert isinstance(result, CreateConferenceOutputDto)
        assert result.success is True
        assert result.conference_id == 1
        mock_conference_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_conference_duplicate_error(
        self, use_case, mock_conference_repository
    ):
        """Test creating a conference with duplicate name and governing body."""
        # Arrange
        existing_conference = Conference(id=1, name="東京都議会", governing_body_id=13)
        mock_conference_repository.get_by_name_and_governing_body.return_value = (
            existing_conference
        )

        input_dto = CreateConferenceInputDto(
            name="東京都議会",
            governing_body_id=13,
        )

        # Act
        result = await use_case.create_conference(input_dto)

        # Assert
        assert result.success is False
        assert "既に存在" in result.error_message
        mock_conference_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_conference_repository_error(
        self, use_case, mock_conference_repository
    ):
        """Test creating a conference when repository raises an error."""
        # Arrange
        mock_conference_repository.get_by_name_and_governing_body.return_value = None
        mock_conference_repository.create.side_effect = Exception("Create failed")

        input_dto = CreateConferenceInputDto(
            name="東京都議会",
            governing_body_id=13,
        )

        # Act
        result = await use_case.create_conference(input_dto)

        # Assert
        assert result.success is False
        assert "Create failed" in result.error_message

    @pytest.mark.asyncio
    async def test_update_conference_success(
        self, use_case, mock_conference_repository
    ):
        """Test updating a conference successfully."""
        # Arrange
        existing_conference = Conference(
            id=1,
            name="東京都議会",
            governing_body_id=13,
        )
        updated_conference = Conference(
            id=1,
            name="東京都議会（更新）",
            governing_body_id=13,
        )
        mock_conference_repository.get_by_id.return_value = existing_conference
        mock_conference_repository.update.return_value = updated_conference

        input_dto = UpdateConferenceInputDto(
            id=1,
            name="東京都議会（更新）",
        )

        # Act
        result = await use_case.update_conference(input_dto)

        # Assert
        assert isinstance(result, UpdateConferenceOutputDto)
        assert result.success is True
        mock_conference_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_conference_not_found(
        self, use_case, mock_conference_repository
    ):
        """Test updating a conference that does not exist."""
        # Arrange
        mock_conference_repository.get_by_id.return_value = None

        input_dto = UpdateConferenceInputDto(
            id=999,
            name="存在しない会議体",
        )

        # Act
        result = await use_case.update_conference(input_dto)

        # Assert
        assert result.success is False
        assert "見つかりません" in result.error_message
        mock_conference_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_conference_repository_error(
        self, use_case, mock_conference_repository
    ):
        """Test updating a conference when repository raises an error."""
        # Arrange
        existing_conference = Conference(id=1, name="東京都議会", governing_body_id=13)
        mock_conference_repository.get_by_id.return_value = existing_conference
        mock_conference_repository.update.side_effect = Exception("Update failed")

        input_dto = UpdateConferenceInputDto(
            id=1,
            name="東京都議会（更新）",
        )

        # Act
        result = await use_case.update_conference(input_dto)

        # Assert
        assert result.success is False
        assert "Update failed" in result.error_message

    @pytest.mark.asyncio
    async def test_delete_conference_success(
        self, use_case, mock_conference_repository
    ):
        """Test deleting a conference successfully."""
        # Arrange
        existing_conference = Conference(id=1, name="東京都議会", governing_body_id=13)
        mock_conference_repository.get_by_id.return_value = existing_conference
        mock_conference_repository.delete.return_value = None

        input_dto = DeleteConferenceInputDto(id=1)

        # Act
        result = await use_case.delete_conference(input_dto)

        # Assert
        assert isinstance(result, DeleteConferenceOutputDto)
        assert result.success is True
        mock_conference_repository.delete.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_conference_not_found(
        self, use_case, mock_conference_repository
    ):
        """Test deleting a conference that does not exist."""
        # Arrange
        mock_conference_repository.get_by_id.return_value = None

        input_dto = DeleteConferenceInputDto(id=999)

        # Act
        result = await use_case.delete_conference(input_dto)

        # Assert
        assert result.success is False
        assert "見つかりません" in result.error_message
        mock_conference_repository.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_conference_repository_error(
        self, use_case, mock_conference_repository
    ):
        """Test deleting a conference when repository raises an error."""
        # Arrange
        existing_conference = Conference(id=1, name="東京都議会", governing_body_id=13)
        mock_conference_repository.get_by_id.return_value = existing_conference
        mock_conference_repository.delete.side_effect = Exception("Delete failed")

        input_dto = DeleteConferenceInputDto(id=1)

        # Act
        result = await use_case.delete_conference(input_dto)

        # Assert
        assert result.success is False
        assert "Delete failed" in result.error_message

    @pytest.mark.asyncio
    async def test_generate_seed_file_success(
        self, use_case, mock_conference_repository, monkeypatch
    ):
        """Test generating seed file successfully."""
        # Arrange
        conferences = [
            Conference(
                id=1,
                name="衆議院本会議",
                governing_body_id=1,
                type="本会議",
            ),
            Conference(
                id=2,
                name="参議院本会議",
                governing_body_id=1,
                type="本会議",
            ),
        ]
        mock_conference_repository.get_all.return_value = conferences

        # Mock open to avoid actual file writing
        m_open = mock_open()
        monkeypatch.setattr("builtins.open", m_open)

        # Act
        result = await use_case.generate_seed_file()

        # Assert
        assert isinstance(result, GenerateSeedFileOutputDto)
        assert result.success is True
        assert "INSERT INTO conferences" in result.seed_content
        assert "衆議院本会議" in result.seed_content
        m_open.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_seed_file_error(self, use_case, mock_conference_repository):
        """Test generating seed file when an error occurs."""
        # Arrange
        mock_conference_repository.get_all.side_effect = Exception("Database error")

        # Act
        result = await use_case.generate_seed_file()

        # Assert
        assert result.success is False
        assert "Database error" in result.error_message
