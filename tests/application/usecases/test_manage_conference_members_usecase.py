"""Tests for ManageConferenceMembersUseCase."""

from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from src.application.dtos.conference_dto import (
    ExtractedConferenceMemberDTO,
)
from src.application.usecases.manage_conference_members_usecase import (
    ManageConferenceMembersUseCase,
)
from src.domain.entities.conference import Conference
from src.domain.entities.politician import Politician


class TestManageConferenceMembersUseCase:
    """Test cases for ManageConferenceMembersUseCase."""

    @pytest.fixture
    def mock_conference_repo(self):
        """Create mock conference repository."""
        repo = AsyncMock()
        repo.get_by_id.return_value = Conference(
            id=1,
            governing_body_id=1,
            name="Test Conference",
            type="委員会",
            members_introduction_url="https://example.com/members",
        )
        return repo

    @pytest.fixture
    def mock_politician_repo(self):
        """Create mock politician repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_conference_service(self):
        """Create mock conference domain service."""
        service = Mock()
        service.extract_member_roles.return_value = {
            "name": "山田太郎",
            "role": "議員",
            "party": "自由民主党",
        }
        return service

    @pytest.fixture
    def mock_extracted_repo(self):
        """Create mock extracted member repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_affiliation_repo(self):
        """Create mock affiliation repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_scraper(self):
        """Create mock web scraper service."""
        scraper = AsyncMock()
        scraper.scrape_text.return_value = """
        <div class="members">
            <div class="member">
                <h3>山田太郎</h3>
                <p>自由民主党 - 議員</p>
            </div>
            <div class="member">
                <h3>佐藤花子</h3>
                <p>立憲民主党 - 委員長</p>
            </div>
        </div>
        """
        return scraper

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM service."""
        llm = AsyncMock()
        llm.extract_conference_members.return_value = [
            {"name": "山田太郎", "party": "自由民主党", "role": "議員"},
            {"name": "佐藤花子", "party": "立憲民主党", "role": "委員長"},
        ]
        llm.match_politician.return_value = {
            "matched": True,
            "confidence": 0.95,
            "politician_id": 1,
        }
        return llm

    @pytest.fixture
    def usecase(
        self,
        mock_conference_repo,
        mock_politician_repo,
        mock_conference_service,
        mock_extracted_repo,
        mock_affiliation_repo,
        mock_scraper,
        mock_llm,
    ):
        """Create use case instance with mocks."""
        return ManageConferenceMembersUseCase(
            conference_repository=mock_conference_repo,
            politician_repository=mock_politician_repo,
            conference_domain_service=mock_conference_service,
            extracted_member_repository=mock_extracted_repo,
            affiliation_repository=mock_affiliation_repo,
            web_scraper_service=mock_scraper,
            llm_service=mock_llm,
        )

    @pytest.mark.asyncio
    async def test_extract_members_success(
        self, usecase, mock_conference_repo, mock_extracted_repo, mock_llm
    ):
        """Test successful member extraction."""
        # Setup
        mock_extracted_repo.create.side_effect = [
            Mock(id=1, name="山田太郎"),
            Mock(id=2, name="佐藤花子"),
        ]

        # Execute
        result = await usecase.extract_members(conference_id=1, force=False)

        # Verify
        assert result["success"] is True
        assert result["extracted_count"] == 2
        assert len(result["members"]) == 2

        # Verify repository calls
        mock_conference_repo.get_by_id.assert_called_once_with(1)
        assert mock_extracted_repo.create.call_count == 2

    @pytest.mark.asyncio
    async def test_extract_members_no_url(self, usecase, mock_conference_repo):
        """Test extraction when conference has no members URL."""
        # Setup
        mock_conference_repo.get_by_id.return_value = Conference(
            id=1,
            governing_body_id=1,
            name="Test Conference",
            type="委員会",
            members_introduction_url=None,
        )

        # Execute
        result = await usecase.extract_members(conference_id=1, force=False)

        # Verify
        assert result["success"] is False
        assert "no members introduction URL" in result["error"]

    @pytest.mark.asyncio
    async def test_extract_members_already_extracted(
        self, usecase, mock_extracted_repo
    ):
        """Test extraction when members already exist and force=False."""
        # Setup
        mock_extracted_repo.get_by_conference.return_value = [
            Mock(id=1, name="Existing Member")
        ]

        # Execute
        result = await usecase.extract_members(conference_id=1, force=False)

        # Verify
        assert result["success"] is False
        assert "already has extracted members" in result["error"]

    @pytest.mark.asyncio
    async def test_extract_members_force_re_extraction(
        self, usecase, mock_extracted_repo, mock_llm
    ):
        """Test forced re-extraction of members."""
        # Setup
        mock_extracted_repo.get_by_conference.return_value = [
            Mock(id=1, name="Old Member")
        ]
        mock_extracted_repo.create.side_effect = [
            Mock(id=2, name="山田太郎"),
            Mock(id=3, name="佐藤花子"),
        ]

        # Execute
        result = await usecase.extract_members(conference_id=1, force=True)

        # Verify
        assert result["success"] is True
        assert result["extracted_count"] == 2

    @pytest.mark.asyncio
    async def test_match_members_with_conference_id(
        self, usecase, mock_extracted_repo, mock_politician_repo, mock_llm
    ):
        """Test matching members for a specific conference."""
        # Setup
        extracted_member = Mock(
            id=1,
            name="山田太郎",
            party_affiliation="自由民主党",
            role="議員",
            conference_id=1,
            matching_status="pending",
            matched_politician_id=None,
            confidence_score=None,
        )
        mock_extracted_repo.get_pending_by_conference.return_value = [extracted_member]

        mock_politician_repo.search.return_value = [
            Politician(id=10, name="山田太郎", speaker_id=1, political_party_id=1)
        ]

        # Execute
        result = await usecase.match_members(conference_id=1)

        # Verify
        assert result["success"] is True
        assert result["matched_count"] == 1
        assert result["needs_review_count"] == 0
        assert result["no_match_count"] == 0

        # Verify repository calls
        mock_extracted_repo.get_pending_by_conference.assert_called_once_with(1)
        mock_extracted_repo.update_matching_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_match_members_all_pending(
        self, usecase, mock_extracted_repo, mock_politician_repo, mock_llm
    ):
        """Test matching all pending members."""
        # Setup
        extracted_members = [
            Mock(
                id=1,
                name="山田太郎",
                party_affiliation="自由民主党",
                role="議員",
                conference_id=1,
                matching_status="pending",
                matched_politician_id=None,
                confidence_score=None,
            ),
            Mock(
                id=2,
                name="佐藤花子",
                party_affiliation="立憲民主党",
                role="委員長",
                conference_id=1,
                matching_status="pending",
                matched_politician_id=None,
                confidence_score=None,
            ),
        ]
        mock_extracted_repo.get_all_pending.return_value = extracted_members

        mock_politician_repo.search.return_value = [
            Politician(id=10, name="山田太郎", speaker_id=1, political_party_id=1)
        ]

        # Execute
        result = await usecase.match_members(conference_id=None)

        # Verify
        assert result["success"] is True
        assert result["matched_count"] == 2

        # Verify repository calls
        mock_extracted_repo.get_all_pending.assert_called_once()
        assert mock_extracted_repo.update_matching_status.call_count == 2

    @pytest.mark.asyncio
    async def test_match_member_to_politician_high_confidence(
        self, usecase, mock_politician_repo, mock_llm
    ):
        """Test matching with high confidence score."""
        # Setup
        member = Mock(
            id=1, name="山田太郎", party_affiliation="自由民主党", role="議員"
        )

        mock_politician_repo.search.return_value = [
            Politician(id=10, name="山田太郎", speaker_id=1, political_party_id=1)
        ]

        mock_llm.match_politician.return_value = {
            "matched": True,
            "confidence": 0.95,
            "politician_id": 10,
        }

        # Execute
        result = await usecase._match_member_to_politician(member)

        # Verify
        assert result["matched"] is True
        assert result["status"] == "matched"
        assert result["politician_id"] == 10
        assert result["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_match_member_to_politician_medium_confidence(
        self, usecase, mock_politician_repo, mock_llm
    ):
        """Test matching with medium confidence score (needs review)."""
        # Setup
        member = Mock(
            id=1, name="山田太郎", party_affiliation="自由民主党", role="議員"
        )

        mock_politician_repo.search.return_value = [
            Politician(
                id=10,
                name="山田太朗",  # Slightly different name
                speaker_id=1,
                political_party_id=1,
            )
        ]

        mock_llm.match_politician.return_value = {
            "matched": True,
            "confidence": 0.6,
            "politician_id": 10,
        }

        # Execute
        result = await usecase._match_member_to_politician(member)

        # Verify
        assert result["matched"] is True
        assert result["status"] == "needs_review"
        assert result["politician_id"] == 10
        assert result["confidence"] == 0.6

    @pytest.mark.asyncio
    async def test_match_member_to_politician_low_confidence(
        self, usecase, mock_politician_repo, mock_llm
    ):
        """Test matching with low confidence score (no match)."""
        # Setup
        member = Mock(
            id=1, name="山田太郎", party_affiliation="自由民主党", role="議員"
        )

        mock_politician_repo.search.return_value = []

        mock_llm.match_politician.return_value = {
            "matched": False,
            "confidence": 0.3,
            "politician_id": None,
        }

        # Execute
        result = await usecase._match_member_to_politician(member)

        # Verify
        assert result["matched"] is False
        assert result["status"] == "no_match"
        assert result["politician_id"] is None
        assert result["confidence"] == 0.3

    @pytest.mark.asyncio
    async def test_create_affiliations_success(
        self, usecase, mock_extracted_repo, mock_affiliation_repo
    ):
        """Test successful creation of affiliations."""
        # Setup
        matched_members = [
            Mock(
                id=1,
                name="山田太郎",
                conference_id=1,
                matched_politician_id=10,
                role="議員",
                matching_status="matched",
            ),
            Mock(
                id=2,
                name="佐藤花子",
                conference_id=1,
                matched_politician_id=20,
                role="委員長",
                matching_status="matched",
            ),
        ]

        mock_extracted_repo.get_by_conference_and_status.return_value = matched_members
        mock_affiliation_repo.find_by_politician_and_conference.return_value = None

        # Execute
        result = await usecase.create_affiliations(
            conference_id=1, start_date=date(2023, 1, 1)
        )

        # Verify
        assert result["success"] is True
        assert result["created_count"] == 2
        assert result["skipped_count"] == 0
        assert len(result["affiliations"]) == 2

        # Verify repository calls
        assert mock_affiliation_repo.create.call_count == 2
        assert mock_extracted_repo.mark_processed.call_count == 2

    @pytest.mark.asyncio
    async def test_create_affiliations_skip_existing(
        self, usecase, mock_extracted_repo, mock_affiliation_repo
    ):
        """Test skipping creation when affiliation already exists."""
        # Setup
        matched_member = Mock(
            id=1,
            name="山田太郎",
            conference_id=1,
            matched_politician_id=10,
            role="議員",
            matching_status="matched",
        )

        mock_extracted_repo.get_by_conference_and_status.return_value = [matched_member]

        # Existing affiliation
        mock_affiliation_repo.find_by_politician_and_conference.return_value = Mock(
            id=100, politician_id=10, conference_id=1
        )

        # Execute
        result = await usecase.create_affiliations(
            conference_id=1, start_date=date(2023, 1, 1)
        )

        # Verify
        assert result["success"] is True
        assert result["created_count"] == 0
        assert result["skipped_count"] == 1

        # Verify no new affiliation was created
        mock_affiliation_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_affiliations_all_conferences(
        self, usecase, mock_extracted_repo, mock_affiliation_repo
    ):
        """Test creating affiliations for all conferences."""
        # Setup
        matched_members = [
            Mock(
                id=1,
                name="山田太郎",
                conference_id=1,
                matched_politician_id=10,
                role="議員",
                matching_status="matched",
            ),
            Mock(
                id=2,
                name="佐藤花子",
                conference_id=2,
                matched_politician_id=20,
                role="委員長",
                matching_status="matched",
            ),
        ]

        mock_extracted_repo.get_by_status.return_value = matched_members
        mock_affiliation_repo.find_by_politician_and_conference.return_value = None

        # Execute
        result = await usecase.create_affiliations(
            conference_id=None, start_date=date(2023, 1, 1)
        )

        # Verify
        assert result["success"] is True
        assert result["created_count"] == 2

        # Verify repository calls
        mock_extracted_repo.get_by_status.assert_called_once_with("matched")

    @pytest.mark.asyncio
    async def test_to_extracted_dto(self, usecase):
        """Test conversion to ExtractedConferenceMemberDTO."""
        # Setup
        entity = Mock(
            id=1,
            name="山田太郎",
            conference_id=1,
            party_affiliation="自由民主党",
            role="議員",
            matching_status="matched",
            matched_politician_id=10,
            confidence_score=0.95,
        )

        # Execute
        dto = usecase._to_extracted_dto(entity)

        # Verify
        assert isinstance(dto, ExtractedConferenceMemberDTO)
        assert dto.id == 1
        assert dto.name == "山田太郎"
        assert dto.conference_id == 1
        assert dto.party_affiliation == "自由民主党"
        assert dto.role == "議員"
        assert dto.matching_status == "matched"
        assert dto.matched_politician_id == 10
        assert dto.confidence_score == 0.95

    @pytest.mark.asyncio
    async def test_error_handling_in_extract_members(self, usecase, mock_scraper):
        """Test error handling during member extraction."""
        # Setup
        mock_scraper.scrape_text.side_effect = Exception("Network error")

        # Execute
        with pytest.raises(Exception) as exc_info:
            await usecase.extract_members(conference_id=1, force=False)

        # Verify
        assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_error_handling_in_match_members(self, usecase, mock_extracted_repo):
        """Test error handling during member matching."""
        # Setup
        mock_extracted_repo.get_pending_by_conference.side_effect = Exception(
            "Database error"
        )

        # Execute
        with pytest.raises(Exception) as exc_info:
            await usecase.match_members(conference_id=1)

        # Verify
        assert "Database error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_extraction_result(self, usecase, mock_llm):
        """Test handling of empty extraction result."""
        # Setup
        mock_llm.extract_conference_members.return_value = []

        # Execute
        result = await usecase.extract_members(conference_id=1, force=False)

        # Verify
        assert result["success"] is True
        assert result["extracted_count"] == 0
        assert len(result["members"]) == 0
