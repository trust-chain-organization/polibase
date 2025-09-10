"""Unit tests for ScrapeProposalUseCase."""

from unittest.mock import create_autospec

import pytest

from src.application.dtos.proposal_dto import (
    ProposalDTO,
    ScrapeProposalInputDTO,
    ScrapeProposalOutputDTO,
)
from src.application.usecases.scrape_proposal_usecase import ScrapeProposalUseCase
from src.domain.entities.proposal import Proposal
from src.domain.repositories.proposal_repository import ProposalRepository
from src.infrastructure.interfaces.proposal_scraper_service import (
    IProposalScraperService,
)


class TestScrapeProposalUseCase:
    """Test suite for ScrapeProposalUseCase."""

    @pytest.fixture
    def mock_proposal_repo(self):
        """Create a mock proposal repository."""
        return create_autospec(ProposalRepository, spec_set=True)

    @pytest.fixture
    def mock_scraper_service(self):
        """Create a mock proposal scraper service."""
        return create_autospec(IProposalScraperService, spec_set=True)

    @pytest.fixture
    def use_case(self, mock_proposal_repo, mock_scraper_service):
        """Create a ScrapeProposalUseCase instance."""
        return ScrapeProposalUseCase(mock_proposal_repo, mock_scraper_service)

    @pytest.mark.asyncio
    async def test_execute_success(self, use_case, mock_scraper_service):
        """Test successful execution of proposal scraping."""
        # Setup
        input_dto = ScrapeProposalInputDTO(
            url="https://www.shugiin.go.jp/test", meeting_id=123
        )

        mock_scraper_service.is_supported_url.return_value = True
        mock_scraper_service.scrape_proposal.return_value = {
            "content": "環境基本法改正案",
            "proposal_number": "第210回国会 第1号",
            "submission_date": "2023-12-01",
            "summary": "環境保護強化法案",
            "url": input_dto.url,
        }

        # Execute
        result = await use_case.execute(input_dto)

        # Assert
        assert isinstance(result, ScrapeProposalOutputDTO)
        assert result.content == "環境基本法改正案"
        assert result.proposal_number == "第210回国会 第1号"
        assert result.submission_date == "2023-12-01"
        assert result.summary == "環境保護強化法案"
        assert result.url == input_dto.url
        assert result.meeting_id == 123

    @pytest.mark.asyncio
    async def test_execute_unsupported_url(self, use_case, mock_scraper_service):
        """Test that unsupported URLs raise ValueError."""
        # Setup
        input_dto = ScrapeProposalInputDTO(url="https://www.google.com")
        mock_scraper_service.is_supported_url.return_value = False

        # Execute and assert
        with pytest.raises(ValueError, match="Unsupported URL"):
            await use_case.execute(input_dto)

    @pytest.mark.asyncio
    async def test_execute_scraping_error(self, use_case, mock_scraper_service):
        """Test that scraping errors are properly handled."""
        # Setup
        input_dto = ScrapeProposalInputDTO(url="https://www.shugiin.go.jp/test")
        mock_scraper_service.is_supported_url.return_value = True
        mock_scraper_service.scrape_proposal.side_effect = Exception("Network error")

        # Execute and assert
        with pytest.raises(RuntimeError, match="Failed to scrape proposal"):
            await use_case.execute(input_dto)

    @pytest.mark.asyncio
    async def test_scrape_and_save_new_proposal(
        self, use_case, mock_proposal_repo, mock_scraper_service
    ):
        """Test scraping and saving a new proposal."""
        # Setup
        input_dto = ScrapeProposalInputDTO(
            url="https://www.shugiin.go.jp/test", meeting_id=123
        )

        mock_scraper_service.is_supported_url.return_value = True
        mock_scraper_service.scrape_proposal.return_value = {
            "content": "環境基本法改正案",
            "proposal_number": "第210回国会 第1号",
            "submission_date": "2023-12-01",
            "summary": "環境保護強化法案",
            "url": input_dto.url,
        }

        # No existing proposal
        mock_proposal_repo.get_by_proposal_number.return_value = None
        mock_proposal_repo.find_by_url.return_value = None

        # Mock saved proposal
        saved_proposal = Proposal(
            id=1,
            content="環境基本法改正案",
            proposal_number="第210回国会 第1号",
            submission_date="2023-12-01",
            summary="環境保護強化法案",
            url=input_dto.url,
            meeting_id=123,
        )
        mock_proposal_repo.create.return_value = saved_proposal

        # Execute
        result = await use_case.scrape_and_save(input_dto)

        # Assert
        assert isinstance(result, ProposalDTO)
        assert result.id == 1
        assert result.content == "環境基本法改正案"
        assert result.proposal_number == "第210回国会 第1号"
        assert result.meeting_id == 123

        # Verify repository calls
        mock_proposal_repo.get_by_proposal_number.assert_called_once_with(
            "第210回国会 第1号"
        )
        mock_proposal_repo.find_by_url.assert_called_once_with(input_dto.url)
        mock_proposal_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_scrape_and_save_existing_proposal_by_number(
        self, use_case, mock_proposal_repo, mock_scraper_service
    ):
        """Test that existing proposals by number are not duplicated."""
        # Setup
        input_dto = ScrapeProposalInputDTO(url="https://www.shugiin.go.jp/test")

        mock_scraper_service.is_supported_url.return_value = True
        mock_scraper_service.scrape_proposal.return_value = {
            "content": "環境基本法改正案",
            "proposal_number": "第210回国会 第1号",
            "url": input_dto.url,
        }

        # Existing proposal found by number
        existing_proposal = Proposal(
            id=1,
            content="環境基本法改正案",
            proposal_number="第210回国会 第1号",
            url="https://old-url.com",
        )
        mock_proposal_repo.get_by_proposal_number.return_value = existing_proposal

        # Execute
        result = await use_case.scrape_and_save(input_dto)

        # Assert
        assert result.id == 1
        assert result.proposal_number == "第210回国会 第1号"

        # Verify save was not called
        mock_proposal_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_scrape_and_save_existing_proposal_by_url(
        self, use_case, mock_proposal_repo, mock_scraper_service
    ):
        """Test that existing proposals by URL are not duplicated."""
        # Setup
        input_dto = ScrapeProposalInputDTO(url="https://www.shugiin.go.jp/test")

        mock_scraper_service.is_supported_url.return_value = True
        mock_scraper_service.scrape_proposal.return_value = {
            "content": "環境基本法改正案",
            "url": input_dto.url,
        }

        # No existing proposal by number, but found by URL
        mock_proposal_repo.get_by_proposal_number.return_value = None
        existing_proposal = Proposal(
            id=2,
            content="環境基本法改正案",
            url=input_dto.url,
        )
        mock_proposal_repo.find_by_url.return_value = existing_proposal

        # Execute
        result = await use_case.scrape_and_save(input_dto)

        # Assert
        assert result.id == 2
        assert result.url == input_dto.url

        # Verify save was not called
        mock_proposal_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_existing_proposal(
        self, use_case, mock_proposal_repo, mock_scraper_service
    ):
        """Test updating an existing proposal with scraped data."""
        # Setup
        proposal_id = 1
        new_url = "https://www.shugiin.go.jp/new"

        # Existing proposal
        existing_proposal = Proposal(
            id=proposal_id,
            content="旧法案",
            meeting_id=123,
        )
        mock_proposal_repo.get_by_id.return_value = existing_proposal

        # Scraped data
        mock_scraper_service.is_supported_url.return_value = True
        mock_scraper_service.scrape_proposal.return_value = {
            "content": "新環境基本法改正案",
            "proposal_number": "第210回国会 第1号",
            "submission_date": "2023-12-01",
            "summary": "環境保護強化法案",
            "url": new_url,
        }

        # Updated proposal
        updated_proposal = Proposal(
            id=proposal_id,
            content="新環境基本法改正案",
            proposal_number="第210回国会 第1号",
            submission_date="2023-12-01",
            summary="環境保護強化法案",
            url=new_url,
            meeting_id=123,
        )
        mock_proposal_repo.update.return_value = updated_proposal

        # Execute
        result = await use_case.update_existing_proposal(proposal_id, new_url)

        # Assert
        assert result.id == proposal_id
        assert result.content == "新環境基本法改正案"
        assert result.url == new_url
        assert result.meeting_id == 123

        # Verify repository calls
        mock_proposal_repo.get_by_id.assert_called_once_with(proposal_id)
        mock_proposal_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_nonexistent_proposal(
        self, use_case, mock_proposal_repo, mock_scraper_service
    ):
        """Test that updating a nonexistent proposal raises ValueError."""
        # Setup
        proposal_id = 999
        url = "https://www.shugiin.go.jp/test"
        mock_proposal_repo.get_by_id.return_value = None

        # Execute and assert
        with pytest.raises(ValueError, match="Proposal with ID 999 not found"):
            await use_case.update_existing_proposal(proposal_id, url)

    def test_entity_to_dto_conversion(self, use_case):
        """Test conversion from Proposal entity to ProposalDTO."""
        # Setup
        proposal = Proposal(
            id=1,
            content="法案内容",
            url="https://example.com",
            submission_date="2023-12-01",
            proposal_number="第1号",
            meeting_id=123,
            summary="概要",
        )

        # Execute
        dto = use_case._entity_to_dto(proposal)

        # Assert
        assert isinstance(dto, ProposalDTO)
        assert dto.id == 1
        assert dto.content == "法案内容"
        assert dto.url == "https://example.com"
        assert dto.submission_date == "2023-12-01"
        assert dto.proposal_number == "第1号"
        assert dto.meeting_id == 123
        assert dto.summary == "概要"
