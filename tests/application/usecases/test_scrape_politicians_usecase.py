"""Tests for ScrapePoliticiansUseCase."""

from unittest.mock import AsyncMock

import pytest

from src.application.dtos.politician_dto import ScrapePoliticiansInputDTO
from src.application.usecases.scrape_politicians_usecase import ScrapePoliticiansUseCase
from src.domain.entities.extracted_politician import ExtractedPolitician
from src.domain.entities.political_party import PoliticalParty


class TestScrapePoliticiansUseCase:
    """Test cases for ScrapePoliticiansUseCase."""

    @pytest.fixture
    def mock_party_repo(self):
        """Create mock political party repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_extracted_politician_repo(self):
        """Create mock extracted politician repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_scraper(self):
        """Create mock web scraper service."""
        scraper = AsyncMock()
        return scraper

    @pytest.fixture
    def use_case(
        self,
        mock_party_repo,
        mock_extracted_politician_repo,
        mock_scraper,
    ):
        """Create ScrapePoliticiansUseCase instance."""
        return ScrapePoliticiansUseCase(
            political_party_repository=mock_party_repo,
            extracted_politician_repository=mock_extracted_politician_repo,
            web_scraper_service=mock_scraper,
        )

    @pytest.mark.asyncio
    async def test_execute_single_party(
        self,
        use_case,
        mock_party_repo,
        mock_extracted_politician_repo,
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

        # No duplicates found
        mock_extracted_politician_repo.get_duplicates.return_value = []

        # Mock created entities
        mock_extracted_politician_repo.create.side_effect = [
            ExtractedPolitician(
                id=1,
                name="山田太郎",
                party_id=1,
                district="東京1区",
                status="pending",
            ),
            ExtractedPolitician(
                id=2,
                name="鈴木花子",
                party_id=1,
                district="比例区",
                status="pending",
            ),
        ]

        # Execute
        request = ScrapePoliticiansInputDTO(party_id=1)
        results = await use_case.execute(request)

        # Verify
        assert len(results) == 2
        assert results[0].name == "山田太郎"
        assert results[0].party_id == 1
        assert results[0].status == "pending"
        assert results[1].name == "鈴木花子"

        mock_scraper.scrape_party_members.assert_called_once_with(
            "https://example.com/members", 1
        )
        assert mock_extracted_politician_repo.get_duplicates.call_count == 2
        assert mock_extracted_politician_repo.create.call_count == 2

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
        mock_extracted_politician_repo,
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
        assert results[0].status == "pending"

        # Should not save anything
        mock_extracted_politician_repo.create.assert_not_called()
        mock_extracted_politician_repo.get_duplicates.assert_not_called()

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
    async def test_skip_duplicate_politician(
        self,
        use_case,
        mock_party_repo,
        mock_extracted_politician_repo,
        mock_scraper,
    ):
        """Test skipping duplicate politician in extracted_politicians table."""
        # Setup
        party = PoliticalParty(
            id=1,
            name="自民党",
            members_list_url="https://example.com/members",
        )
        existing_extracted = ExtractedPolitician(
            id=10,
            name="山田太郎",
            party_id=1,
            status="pending",
        )

        mock_party_repo.get_by_id.return_value = party
        mock_scraper.scrape_party_members.return_value = [
            {
                "name": "山田太郎",
                "position": "衆議院議員",
                "district": "東京1区",
            },
        ]

        # Duplicate exists - should skip
        mock_extracted_politician_repo.get_duplicates.return_value = [
            existing_extracted
        ]

        # Execute
        request = ScrapePoliticiansInputDTO(party_id=1)
        results = await use_case.execute(request)

        # Verify
        assert len(results) == 0  # Skipped duplicate
        mock_extracted_politician_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_new_politician_no_duplicate(
        self,
        use_case,
        mock_party_repo,
        mock_extracted_politician_repo,
        mock_scraper,
    ):
        """Test creating new politician when no duplicate exists."""
        # Setup
        party = PoliticalParty(
            id=1,
            name="自民党",
            members_list_url="https://example.com/members",
        )
        new_extracted = ExtractedPolitician(
            id=10,
            name="山田太郎",
            party_id=1,
            district="東京1区",
            status="pending",
        )

        mock_party_repo.get_by_id.return_value = party
        mock_scraper.scrape_party_members.return_value = [
            {
                "name": "山田太郎",
                "position": "衆議院議員",
                "district": "東京1区",
            },
        ]

        # No duplicate found - should create new
        mock_extracted_politician_repo.get_duplicates.return_value = []
        mock_extracted_politician_repo.create.return_value = new_extracted

        # Execute
        request = ScrapePoliticiansInputDTO(party_id=1)
        results = await use_case.execute(request)

        # Verify
        assert len(results) == 1
        assert results[0].name == "山田太郎"
        mock_extracted_politician_repo.create.assert_called_once()

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
