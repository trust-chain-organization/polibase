"""Tests for ScrapePoliticiansUseCase."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dtos.politician_dto import ScrapePoliticiansInputDTO
from src.application.usecases.scrape_politicians_usecase import ScrapePoliticiansUseCase
from src.domain.entities.political_party import PoliticalParty
from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker


class TestScrapePoliticiansUseCase:
    """Test cases for ScrapePoliticiansUseCase."""

    @pytest.fixture
    def mock_party_repo(self):
        """Create mock political party repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_politician_repo(self):
        """Create mock politician repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_speaker_repo(self):
        """Create mock speaker repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_politician_service(self):
        """Create mock politician domain service."""
        service = MagicMock()
        return service

    @pytest.fixture
    def mock_scraper(self):
        """Create mock web scraper service."""
        scraper = AsyncMock()
        return scraper

    @pytest.fixture
    def use_case(
        self,
        mock_party_repo,
        mock_politician_repo,
        mock_speaker_repo,
        mock_politician_service,
        mock_scraper,
    ):
        """Create ScrapePoliticiansUseCase instance."""
        return ScrapePoliticiansUseCase(
            political_party_repository=mock_party_repo,
            politician_repository=mock_politician_repo,
            speaker_repository=mock_speaker_repo,
            politician_domain_service=mock_politician_service,
            web_scraper_service=mock_scraper,
        )

    @pytest.mark.asyncio
    async def test_execute_single_party(
        self,
        use_case,
        mock_party_repo,
        mock_politician_repo,
        mock_speaker_repo,
        mock_scraper,
    ):
        """Test scraping politicians from a single party."""
        # Setup
        party = PoliticalParty(
            id=1,
            name="自民党",
            members_list_url="https://example.com/members",
        )

        mock_party_repo.get_by_id.return_value = party
        mock_scraper.scrape_party_members.return_value = [
            {
                "name": "山田太郎",
                "position": "衆議院議員",
                "district": "東京1区",
            },
            {
                "name": "鈴木花子",
                "position": "参議院議員",
                "district": "比例区",
            },
        ]

        mock_politician_repo.get_by_name_and_party.return_value = None
        mock_speaker_repo.upsert.side_effect = [
            Speaker(id=100, name="山田太郎", is_politician=True),
            Speaker(id=101, name="鈴木花子", is_politician=True),
        ]
        mock_politician_repo.create.side_effect = [
            Politician(
                id=1,
                name="山田太郎",
                speaker_id=100,
                political_party_id=1,
                position="衆議院議員",
                district="東京1区",
            ),
            Politician(
                id=2,
                name="鈴木花子",
                speaker_id=101,
                political_party_id=1,
                position="参議院議員",
                district="比例区",
            ),
        ]

        # Execute
        request = ScrapePoliticiansInputDTO(party_id=1)
        results = await use_case.execute(request)

        # Verify
        assert len(results) == 2
        assert results[0].name == "山田太郎"
        assert results[0].political_party_id == 1
        assert results[1].name == "鈴木花子"

        mock_scraper.scrape_party_members.assert_called_once_with(
            "https://example.com/members", 1, "自民党"
        )
        assert mock_speaker_repo.upsert.call_count == 2
        assert mock_politician_repo.create.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_all_parties(self, use_case, mock_party_repo, mock_scraper):
        """Test scraping politicians from all parties."""
        # Setup
        parties = [
            PoliticalParty(
                id=1,
                name="自民党",
                members_list_url="https://example.com/jimin",
            ),
            PoliticalParty(
                id=2,
                name="立憲民主党",
                members_list_url="https://example.com/cdp",
            ),
        ]

        mock_party_repo.get_with_members_url.return_value = parties
        mock_scraper.scrape_party_members.return_value = []

        # Execute
        request = ScrapePoliticiansInputDTO(all_parties=True)
        await use_case.execute(request)

        # Verify
        assert mock_scraper.scrape_party_members.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_dry_run(
        self,
        use_case,
        mock_party_repo,
        mock_politician_repo,
        mock_speaker_repo,
        mock_scraper,
    ):
        """Test dry run mode without saving."""
        # Setup
        party = PoliticalParty(
            id=1,
            name="自民党",
            members_list_url="https://example.com/members",
        )

        mock_party_repo.get_by_id.return_value = party
        mock_scraper.scrape_party_members.return_value = [
            {"name": "山田太郎", "position": "衆議院議員"},
        ]

        # Execute
        request = ScrapePoliticiansInputDTO(party_id=1, dry_run=True)
        results = await use_case.execute(request)

        # Verify
        assert len(results) == 1
        assert results[0].id == 0  # Not saved
        assert results[0].speaker_id == 0  # Not created

        # Should not save anything
        mock_politician_repo.create.assert_not_called()
        mock_speaker_repo.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_party_not_found(self, use_case, mock_party_repo):
        """Test error when party not found."""
        # Setup
        mock_party_repo.get_by_id.return_value = None

        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            request = ScrapePoliticiansInputDTO(party_id=999)
            await use_case.execute(request)

        assert "Party 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_no_params_error(self, use_case):
        """Test error when neither party_id nor all_parties specified."""
        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            request = ScrapePoliticiansInputDTO()
            await use_case.execute(request)

        assert "Either party_id or all_parties must be specified" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_existing_politician(
        self,
        use_case,
        mock_party_repo,
        mock_politician_repo,
        mock_politician_service,
        mock_scraper,
    ):
        """Test updating existing politician with new information."""
        # Setup
        party = PoliticalParty(
            id=1,
            name="自民党",
            members_list_url="https://example.com/members",
        )
        existing_politician = Politician(
            id=10,
            name="山田太郎",
            speaker_id=100,
            political_party_id=1,
            position=None,  # Missing info
        )

        mock_party_repo.get_by_id.return_value = party
        mock_scraper.scrape_party_members.return_value = [
            {
                "name": "山田太郎",
                "position": "衆議院議員",  # New info
                "district": "東京1区",
            },
        ]

        mock_politician_repo.get_by_name_and_party.return_value = existing_politician
        mock_politician_repo.get_by_party.return_value = [existing_politician]
        mock_politician_service.is_duplicate_politician.return_value = (
            existing_politician
        )

        merged_politician = Politician(
            id=10,
            name="山田太郎",
            speaker_id=100,
            political_party_id=1,
            position="衆議院議員",
            district="東京1区",
        )
        mock_politician_service.merge_politician_info.return_value = merged_politician
        mock_politician_repo.update.return_value = merged_politician

        # Execute
        request = ScrapePoliticiansInputDTO(party_id=1)
        results = await use_case.execute(request)

        # Verify
        assert len(results) == 1
        assert results[0].position == "衆議院議員"
        mock_politician_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_duplicate_without_new_info(
        self,
        use_case,
        mock_party_repo,
        mock_politician_repo,
        mock_politician_service,
        mock_scraper,
    ):
        """Test skipping duplicate politician without new information."""
        # Setup
        party = PoliticalParty(
            id=1,
            name="自民党",
            members_list_url="https://example.com/members",
        )
        existing_politician = Politician(
            id=10,
            name="山田太郎",
            speaker_id=100,
            political_party_id=1,
            position="衆議院議員",
            district="東京1区",
        )

        mock_party_repo.get_by_id.return_value = party
        mock_scraper.scrape_party_members.return_value = [
            {
                "name": "山田太郎",
                "position": "衆議院議員",  # Same info
                "district": "東京1区",
            },
        ]

        mock_politician_repo.get_by_name_and_party.return_value = existing_politician
        mock_politician_repo.get_by_party.return_value = [existing_politician]
        mock_politician_service.is_duplicate_politician.return_value = (
            existing_politician
        )

        # Execute
        request = ScrapePoliticiansInputDTO(party_id=1)
        results = await use_case.execute(request)

        # Verify
        assert len(results) == 0  # Skipped
        mock_politician_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_scrape_party_no_url(self, use_case, mock_party_repo):
        """Test handling party without members URL."""
        # Setup
        party = PoliticalParty(
            id=1,
            name="無所属",
            members_list_url=None,  # No URL
        )

        mock_party_repo.get_by_id.return_value = party

        # Execute
        request = ScrapePoliticiansInputDTO(party_id=1)
        results = await use_case.execute(request)

        # Verify
        assert len(results) == 0
