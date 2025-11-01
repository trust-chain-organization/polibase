"""Tests for ManagePoliticalPartiesUseCase."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.application.usecases.manage_political_parties_usecase import (
    GenerateSeedFileOutputDto,
    ManagePoliticalPartiesUseCase,
    PoliticalPartyListInputDto,
    PoliticalPartyListOutputDto,
    UpdatePoliticalPartyUrlInputDto,
    UpdatePoliticalPartyUrlOutputDto,
)
from src.domain.entities.political_party import PoliticalParty


class TestManagePoliticalPartiesUseCase:
    """Test cases for ManagePoliticalPartiesUseCase."""

    @pytest.fixture
    def mock_party_repository(self):
        """Create mock political party repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def use_case(self, mock_party_repository):
        """Create ManagePoliticalPartiesUseCase instance."""
        return ManagePoliticalPartiesUseCase(repository=mock_party_repository)

    @pytest.mark.asyncio
    async def test_list_parties_all(self, use_case, mock_party_repository):
        """Test listing all political parties."""
        # Arrange
        parties = [
            PoliticalParty(
                id=1, name="自民党", members_list_url="http://example.com/1"
            ),
            PoliticalParty(
                id=2, name="立憲民主党", members_list_url="http://example.com/2"
            ),
            PoliticalParty(id=3, name="日本維新の会", members_list_url=None),
        ]
        mock_party_repository.get_all.return_value = parties

        input_dto = PoliticalPartyListInputDto(filter_type="all")

        # Act
        result = await use_case.list_parties(input_dto)

        # Assert
        assert isinstance(result, PoliticalPartyListOutputDto)
        assert len(result.parties) == 3
        assert result.statistics.total == 3
        assert result.statistics.with_url == 2
        assert result.statistics.without_url == 1

    @pytest.mark.asyncio
    async def test_list_parties_with_url(self, use_case, mock_party_repository):
        """Test listing parties with URL."""
        # Arrange
        parties = [
            PoliticalParty(
                id=1, name="自民党", members_list_url="http://example.com/1"
            ),
            PoliticalParty(
                id=2, name="立憲民主党", members_list_url="http://example.com/2"
            ),
            PoliticalParty(id=3, name="日本維新の会", members_list_url=None),
        ]
        mock_party_repository.get_all.return_value = parties

        input_dto = PoliticalPartyListInputDto(filter_type="with_url")

        # Act
        result = await use_case.list_parties(input_dto)

        # Assert
        assert len(result.parties) == 2
        assert all(p.members_list_url is not None for p in result.parties)

    @pytest.mark.asyncio
    async def test_list_parties_without_url(self, use_case, mock_party_repository):
        """Test listing parties without URL."""
        # Arrange
        parties = [
            PoliticalParty(
                id=1, name="自民党", members_list_url="http://example.com/1"
            ),
            PoliticalParty(
                id=2, name="立憲民主党", members_list_url="http://example.com/2"
            ),
            PoliticalParty(id=3, name="日本維新の会", members_list_url=None),
        ]
        mock_party_repository.get_all.return_value = parties

        input_dto = PoliticalPartyListInputDto(filter_type="without_url")

        # Act
        result = await use_case.list_parties(input_dto)

        # Assert
        assert len(result.parties) == 1
        assert result.parties[0].members_list_url is None

    @pytest.mark.asyncio
    async def test_list_parties_empty(self, use_case, mock_party_repository):
        """Test listing parties when no parties exist."""
        # Arrange
        mock_party_repository.get_all.return_value = []

        input_dto = PoliticalPartyListInputDto()

        # Act
        result = await use_case.list_parties(input_dto)

        # Assert
        assert len(result.parties) == 0
        assert result.statistics.total == 0

    @pytest.mark.asyncio
    async def test_list_parties_sorted_by_name(self, use_case, mock_party_repository):
        """Test that parties are sorted by name."""
        # Arrange
        parties = [
            PoliticalParty(id=3, name="立憲民主党"),
            PoliticalParty(id=1, name="自民党"),
            PoliticalParty(id=2, name="公明党"),
        ]
        mock_party_repository.get_all.return_value = parties

        input_dto = PoliticalPartyListInputDto()

        # Act
        result = await use_case.list_parties(input_dto)

        # Assert
        # Parties should be sorted by name
        party_names = [p.name for p in result.parties]
        assert party_names == sorted(party_names)

    @pytest.mark.asyncio
    async def test_update_party_url_success(self, use_case, mock_party_repository):
        """Test updating party URL successfully."""
        # Arrange
        party = PoliticalParty(id=1, name="自民党", members_list_url=None)
        updated_party = PoliticalParty(
            id=1, name="自民党", members_list_url="http://example.com/new"
        )
        mock_party_repository.get_by_id.return_value = party
        mock_party_repository.update.return_value = updated_party

        input_dto = UpdatePoliticalPartyUrlInputDto(
            party_id=1, members_list_url="http://example.com/new"
        )

        # Act
        result = await use_case.update_party_url(input_dto)

        # Assert
        assert isinstance(result, UpdatePoliticalPartyUrlOutputDto)
        assert result.success is True
        assert result.party.members_list_url == "http://example.com/new"
        mock_party_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_party_url_not_found(self, use_case, mock_party_repository):
        """Test updating URL for non-existent party."""
        # Arrange
        mock_party_repository.get_by_id.return_value = None

        input_dto = UpdatePoliticalPartyUrlInputDto(
            party_id=999, members_list_url="http://example.com/new"
        )

        # Act
        result = await use_case.update_party_url(input_dto)

        # Assert
        assert result.success is False
        assert "見つかりません" in result.message
        mock_party_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_party_url_repository_error(
        self, use_case, mock_party_repository
    ):
        """Test updating URL when repository raises an error."""
        # Arrange
        party = PoliticalParty(id=1, name="自民党")
        mock_party_repository.get_by_id.return_value = party
        mock_party_repository.update.side_effect = Exception("Update failed")

        input_dto = UpdatePoliticalPartyUrlInputDto(
            party_id=1, members_list_url="http://example.com/new"
        )

        # Act
        result = await use_case.update_party_url(input_dto)

        # Assert
        assert result.success is False
        assert "エラー" in result.message

    def test_generate_seed_file_success(self, use_case, monkeypatch):
        """Test generating seed file successfully."""
        # Arrange
        mock_generator_instance = Mock()
        mock_generator_instance.generate_political_parties_seed.return_value = (
            "-- Political Parties Seed\nINSERT INTO..."
        )

        mock_generator_class = Mock(return_value=mock_generator_instance)

        # Monkeypatch the SeedGenerator class
        monkeypatch.setattr(
            "src.application.usecases.manage_political_parties_usecase.SeedGenerator",
            mock_generator_class,
        )

        # Act
        result = use_case.generate_seed_file()

        # Assert
        assert isinstance(result, GenerateSeedFileOutputDto)
        assert result.success is True
        assert "INSERT INTO" in result.content
        mock_generator_class.assert_called_once()
        mock_generator_instance.generate_political_parties_seed.assert_called_once()

    def test_generate_seed_file_error(self, use_case, monkeypatch):
        """Test generating seed file when an error occurs."""

        # Arrange
        def mock_seed_generator_init():
            raise Exception("Generation failed")

        # Monkeypatch the SeedGenerator class to raise an exception
        monkeypatch.setattr(
            "src.application.usecases.manage_political_parties_usecase.SeedGenerator",
            mock_seed_generator_init,
        )

        # Act
        result = use_case.generate_seed_file()

        # Assert
        assert result.success is False
        assert "エラー" in result.message

    @pytest.mark.asyncio
    async def test_list_parties_handles_none_name(
        self, use_case, mock_party_repository
    ):
        """Test listing parties with None name (edge case)."""
        # Arrange
        parties = [
            PoliticalParty(id=1, name=None),
            PoliticalParty(id=2, name="自民党"),
        ]
        mock_party_repository.get_all.return_value = parties

        input_dto = PoliticalPartyListInputDto()

        # Act
        result = await use_case.list_parties(input_dto)

        # Assert
        assert len(result.parties) == 2
        # Should not raise an error even with None name
