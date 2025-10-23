"""Tests for ScrapePoliticiansUseCase."""

from unittest.mock import AsyncMock

import pytest

from src.application.dtos.politician_dto import ScrapePoliticiansInputDTO
from src.application.usecases.scrape_politicians_usecase import ScrapePoliticiansUseCase
from src.domain.entities.party_scraping_state import PartyScrapingState
from src.domain.entities.political_party import PoliticalParty
from src.domain.entities.politician_party_extracted_politician import (
    PoliticianPartyExtractedPolitician,
)


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
    def mock_scraping_agent(self):
        """Create mock party scraping agent."""
        agent = AsyncMock()
        return agent

    @pytest.fixture
    def use_case(
        self,
        mock_party_repo,
        mock_extracted_politician_repo,
        mock_scraping_agent,
    ):
        """Create ScrapePoliticiansUseCase instance."""
        return ScrapePoliticiansUseCase(
            political_party_repository=mock_party_repo,
            extracted_politician_repository=mock_extracted_politician_repo,
            party_scraping_agent=mock_scraping_agent,
        )

    @pytest.mark.asyncio
    async def test_execute_single_party(
        self,
        use_case,
        mock_party_repo,
        mock_extracted_politician_repo,
        mock_scraping_agent,
    ):
        """Test scraping politicians from a single party."""
        # Setup
        party = PoliticalParty(
            id=1,
            name="自民党",
            members_list_url="https://example.com/members",
        )

        mock_party_repo.get_by_id.return_value = party

        # Mock LangGraph agent response
        final_state = PartyScrapingState(
            party_id=1,
            party_name="自民党",
            current_url="https://example.com/members",
            max_depth=3,
        )
        # Add extracted members using the proper API
        final_state.add_extracted_member(
            {
                "name": "山田太郎",
                "position": "衆議院議員",
                "electoral_district": "東京1区",
            }
        )
        final_state.add_extracted_member(
            {
                "name": "鈴木花子",
                "position": "参議院議員",
                "electoral_district": "比例区",
            }
        )
        mock_scraping_agent.scrape.return_value = final_state

        # No duplicates found
        mock_extracted_politician_repo.get_duplicates.return_value = []

        # Mock created entities
        mock_extracted_politician_repo.create.side_effect = [
            PoliticianPartyExtractedPolitician(
                id=1,
                name="山田太郎",
                party_id=1,
                district="東京1区",
                status="pending",
            ),
            PoliticianPartyExtractedPolitician(
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

        # Verify LangGraph agent was called correctly
        mock_scraping_agent.scrape.assert_called_once()
        call_args = mock_scraping_agent.scrape.call_args[0][0]
        assert call_args.party_id == 1
        assert call_args.party_name == "自民党"
        assert call_args.current_url == "https://example.com/members"

        assert mock_extracted_politician_repo.get_duplicates.call_count == 2
        assert mock_extracted_politician_repo.create.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_all_parties(
        self, use_case, mock_party_repo, mock_scraping_agent
    ):
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

        # Mock LangGraph agent to return empty results
        empty_state = PartyScrapingState(
            party_id=1,
            party_name="",
            current_url="https://example.com",
            max_depth=3,
        )
        mock_scraping_agent.scrape.return_value = empty_state

        # Execute
        request = ScrapePoliticiansInputDTO(all_parties=True)
        await use_case.execute(request)

        # Verify
        assert mock_scraping_agent.scrape.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_dry_run(
        self,
        use_case,
        mock_party_repo,
        mock_extracted_politician_repo,
        mock_scraping_agent,
    ):
        """Test dry run mode without saving."""
        # Setup
        party = PoliticalParty(
            id=1,
            name="自民党",
            members_list_url="https://example.com/members",
        )

        mock_party_repo.get_by_id.return_value = party

        # Mock LangGraph agent response
        final_state = PartyScrapingState(
            party_id=1,
            party_name="自民党",
            current_url="https://example.com/members",
            max_depth=3,
        )
        final_state.add_extracted_member({"name": "山田太郎", "position": "衆議院議員"})
        mock_scraping_agent.scrape.return_value = final_state

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
        mock_scraping_agent,
    ):
        """Test skipping duplicate politician in extracted_politicians table."""
        # Setup
        party = PoliticalParty(
            id=1,
            name="自民党",
            members_list_url="https://example.com/members",
        )
        existing_extracted = PoliticianPartyExtractedPolitician(
            id=10,
            name="山田太郎",
            party_id=1,
            status="pending",
        )

        mock_party_repo.get_by_id.return_value = party

        # Mock LangGraph agent response
        final_state = PartyScrapingState(
            party_id=1,
            party_name="自民党",
            current_url="https://example.com/members",
            max_depth=3,
        )
        final_state.add_extracted_member(
            {
                "name": "山田太郎",
                "position": "衆議院議員",
                "electoral_district": "東京1区",
            }
        )
        mock_scraping_agent.scrape.return_value = final_state

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
        mock_scraping_agent,
    ):
        """Test creating new politician when no duplicate exists."""
        # Setup
        party = PoliticalParty(
            id=1,
            name="自民党",
            members_list_url="https://example.com/members",
        )
        new_extracted = PoliticianPartyExtractedPolitician(
            id=10,
            name="山田太郎",
            party_id=1,
            district="東京1区",
            status="pending",
        )

        mock_party_repo.get_by_id.return_value = party

        # Mock LangGraph agent response
        final_state = PartyScrapingState(
            party_id=1,
            party_name="自民党",
            current_url="https://example.com/members",
            max_depth=3,
        )
        final_state.add_extracted_member(
            {
                "name": "山田太郎",
                "position": "衆議院議員",
                "electoral_district": "東京1区",
            }
        )
        mock_scraping_agent.scrape.return_value = final_state

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
