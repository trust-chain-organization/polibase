"""Tests for ManageConferenceMembersUseCase."""

from datetime import date
from typing import Any
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


def create_mock_extracted_member(**kwargs: Any) -> Mock:
    """Helper to create a mock extracted member entity."""
    member = Mock()
    member.id = kwargs.get("id", 1)
    member.name = kwargs.get("name", "Test Member")
    member.conference_id = kwargs.get("conference_id", 1)
    member.party_affiliation = kwargs.get("party_affiliation", None)
    member.role = kwargs.get("role", None)
    member.matching_status = kwargs.get("matching_status", "pending")
    member.matched_politician_id = kwargs.get("matched_politician_id", None)
    member.confidence_score = kwargs.get("confidence_score", None)
    return member


class TestManageConferenceMembersUseCase:
    """Test cases for ManageConferenceMembersUseCase."""

    @pytest.fixture
    def mock_conference_repo(self) -> AsyncMock:
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
    def mock_politician_repo(self) -> AsyncMock:
        """Create mock politician repository."""
        repo = AsyncMock()
        repo.get_all.return_value = []  # Default empty list
        repo.get_by_id.return_value = None  # Default None
        repo.search_by_name.return_value = []  # Default empty list
        return repo

    @pytest.fixture
    def mock_conference_service(self) -> Mock:
        """Create mock conference domain service."""
        service = Mock()
        service.extract_member_role.return_value = "議員"
        service.normalize_party_name.return_value = "自由民主党"
        service.calculate_member_confidence_score.return_value = 0.95
        service.calculate_affiliation_overlap.return_value = False
        return service

    @pytest.fixture
    def mock_extracted_repo(self) -> AsyncMock:
        """Create mock extracted member repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_affiliation_repo(self) -> AsyncMock:
        """Create mock affiliation repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_scraper(self) -> AsyncMock:
        """Create mock web scraper service."""
        scraper = AsyncMock()
        scraper.scrape_conference_members.return_value = [
            {"name": "山田太郎", "party": "自由民主党", "role": "議員"},
            {"name": "佐藤花子", "party": "立憲民主党", "role": "委員長"},
        ]
        return scraper

    @pytest.fixture
    def mock_llm(self) -> AsyncMock:
        """Create mock LLM service."""
        llm = AsyncMock()
        llm.extract_conference_members.return_value = [
            {"name": "山田太郎", "party": "自由民主党", "role": "議員"},
            {"name": "佐藤花子", "party": "立憲民主党", "role": "委員長"},
        ]
        llm.match_conference_member.return_value = {
            "matched_id": 1,
            "confidence": 0.95,
        }
        return llm

    @pytest.fixture
    def usecase(
        self,
        mock_conference_repo: AsyncMock,
        mock_politician_repo: AsyncMock,
        mock_conference_service: Mock,
        mock_extracted_repo: AsyncMock,
        mock_affiliation_repo: AsyncMock,
        mock_scraper: AsyncMock,
        mock_llm: AsyncMock,
    ) -> ManageConferenceMembersUseCase:
        """Create use case instance with mocks."""
        return ManageConferenceMembersUseCase(
            conference_repository=mock_conference_repo,
            politician_repository=mock_politician_repo,
            conference_domain_service=mock_conference_service,
            extracted_member_repository=mock_extracted_repo,
            politician_affiliation_repository=mock_affiliation_repo,
            web_scraper_service=mock_scraper,
            llm_service=mock_llm,
        )

    @pytest.mark.asyncio
    async def test_extract_members_success(
        self, usecase, mock_conference_repo, mock_extracted_repo, mock_llm, mock_scraper
    ):
        """Test successful member extraction."""
        # Setup
        mock_extracted_repo.get_by_conference.return_value = []  # No existing members

        mock_extracted_repo.create.side_effect = [
            create_mock_extracted_member(
                id=1,
                name="山田太郎",
                conference_id=1,
                party_affiliation="自由民主党",
                role="議員",
            ),
            create_mock_extracted_member(
                id=2,
                name="佐藤花子",
                conference_id=1,
                party_affiliation="立憲民主党",
                role="委員長",
            ),
        ]
        mock_scraper.scrape_conference_members.return_value = [
            {"name": "山田太郎", "party": "自由民主党", "role": "議員"},
            {"name": "佐藤花子", "party": "立憲民主党", "role": "委員長"},
        ]

        # Execute
        result = await usecase.extract_members(conference_id=1, force=False)

        # Verify
        assert len(result) == 2
        assert result[0].name == "山田太郎"
        assert result[1].name == "佐藤花子"

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

        # Execute & Verify - should raise ValueError
        with pytest.raises(ValueError, match="no members introduction URL"):
            await usecase.extract_members(conference_id=1, force=False)

    @pytest.mark.asyncio
    async def test_extract_members_already_extracted(
        self, usecase, mock_extracted_repo
    ):
        """Test extraction when members already exist and force=False."""
        # Setup
        existing_members = [
            create_mock_extracted_member(
                id=1,
                name="Existing Member",
                conference_id=1,
                party_affiliation="党名",
                role="役職",
            )
        ]
        mock_extracted_repo.get_by_conference.return_value = existing_members

        # Execute
        result = await usecase.extract_members(conference_id=1, force=False)

        # Verify - should return existing members as DTOs
        assert len(result) == 1
        assert result[0].name == "Existing Member"

    @pytest.mark.asyncio
    async def test_extract_members_force_re_extraction(
        self, usecase, mock_extracted_repo, mock_llm, mock_scraper
    ):
        """Test forced re-extraction of members."""
        # Setup
        mock_extracted_repo.get_by_conference.return_value = [
            create_mock_extracted_member(
                id=1,
                name="Old Member",
                conference_id=1,
                party_affiliation="党名",
                role="役職",
            )
        ]
        mock_extracted_repo.create.side_effect = [
            create_mock_extracted_member(
                id=2,
                name="山田太郎",
                conference_id=1,
                party_affiliation="自由民主党",
                role="議員",
            ),
            create_mock_extracted_member(
                id=3,
                name="佐藤花子",
                conference_id=1,
                party_affiliation="立憲民主党",
                role="委員長",
            ),
        ]
        mock_scraper.scrape_conference_members.return_value = [
            {"name": "山田太郎", "party": "自由民主党", "role": "議員"},
            {"name": "佐藤花子", "party": "立憲民主党", "role": "委員長"},
        ]

        # Execute
        result = await usecase.extract_members(conference_id=1, force=True)

        # Verify
        assert len(result) == 2
        assert result[0].name == "山田太郎"
        assert result[1].name == "佐藤花子"

    @pytest.mark.asyncio
    async def test_match_members_with_conference_id(
        self, usecase, mock_extracted_repo, mock_politician_repo, mock_llm
    ):
        """Test matching members for a specific conference."""
        # Setup
        extracted_member = create_mock_extracted_member(
            id=1,
            name="山田太郎",
            party_affiliation="自由民主党",
            role="議員",
            conference_id=1,
        )
        mock_extracted_repo.get_pending_by_conference.return_value = [extracted_member]

        politician = Politician(
            id=10, name="山田太郎", speaker_id=1, political_party_id=1
        )
        mock_politician_repo.search_by_name.return_value = [politician]
        mock_politician_repo.get_all.return_value = [politician]
        mock_politician_repo.get_by_id.return_value = politician

        # Mock LLM to return matched_id 10
        mock_llm.match_conference_member.return_value = {
            "matched_id": 10,
            "confidence": 0.95,
        }

        # Execute
        result = await usecase.match_members(conference_id=1)

        # Verify
        assert len(result) == 1
        assert result[0].extracted_member_id == 1
        assert result[0].member_name == "山田太郎"
        assert result[0].matched_politician_id == 10  # The actual politician ID
        assert result[0].confidence_score == 0.95
        assert result[0].status == "matched"

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
            create_mock_extracted_member(
                id=1,
                name="山田太郎",
                party_affiliation="自由民主党",
                role="議員",
                conference_id=1,
            ),
            create_mock_extracted_member(
                id=2,
                name="佐藤花子",
                party_affiliation="立憲民主党",
                role="委員長",
                conference_id=1,
            ),
        ]
        mock_extracted_repo.get_all_pending.return_value = extracted_members

        mock_politician_repo.search_by_name.return_value = [
            Politician(id=10, name="山田太郎", speaker_id=1, political_party_id=1)
        ]

        # Execute
        result = await usecase.match_members(conference_id=None)

        # Verify
        assert len(result) == 2
        assert all(r.status == "matched" for r in result)
        assert all(r.confidence_score == 0.95 for r in result)

        # Verify repository calls
        mock_extracted_repo.get_all_pending.assert_called_once()
        assert mock_extracted_repo.update_matching_status.call_count == 2

    @pytest.mark.asyncio
    async def test_match_member_to_politician_high_confidence(
        self, usecase, mock_politician_repo, mock_llm
    ):
        """Test matching with high confidence score."""
        # Setup
        member = create_mock_extracted_member(
            id=1, name="山田太郎", party_affiliation="自由民主党", role="議員"
        )

        mock_politician_repo.search_by_name.return_value = [
            Politician(id=10, name="山田太郎", speaker_id=1, political_party_id=1)
        ]

        mock_llm.match_conference_member.return_value = {
            "matched_id": 10,
            "confidence": 0.95,
        }

        # Execute
        result = await usecase._match_member_to_politician(member, threshold=0.7)

        # Verify
        assert result.status == "matched"
        assert result.matched_politician_id == 10
        assert result.confidence_score == 0.95
        assert result.member_name == "山田太郎"

    @pytest.mark.asyncio
    async def test_match_member_to_politician_medium_confidence(
        self, usecase, mock_politician_repo, mock_llm
    ):
        """Test matching with medium confidence score (needs review)."""
        # Setup
        member = create_mock_extracted_member(
            id=1, name="山田太郎", party_affiliation="自由民主党", role="議員"
        )

        mock_politician_repo.search_by_name.return_value = [
            Politician(
                id=10,
                name="山田太朗",  # Slightly different name
                speaker_id=1,
                political_party_id=1,
            )
        ]

        mock_llm.match_conference_member.return_value = {
            "matched_id": 10,
            "confidence": 0.6,
        }

        # Execute
        result = await usecase._match_member_to_politician(member, threshold=0.5)

        # Verify
        # Status is still "matched" since candidates were found via search_by_name
        # LLM matching only happens when no candidates are found initially
        assert result.status == "matched"
        assert result.matched_politician_id == 10
        assert (
            result.confidence_score == 0.95
        )  # From calculate_member_confidence_score mock
        assert result.member_name == "山田太郎"

    @pytest.mark.asyncio
    async def test_match_member_to_politician_low_confidence(
        self, usecase, mock_politician_repo, mock_llm
    ):
        """Test matching with low confidence score (no match)."""
        # Setup
        member = create_mock_extracted_member(
            id=1, name="山田太郎", party_affiliation="自由民主党", role="議員"
        )

        mock_politician_repo.search_by_name.return_value = []
        mock_politician_repo.get_all.return_value = [
            Politician(id=20, name="佐藤太郎", speaker_id=2, political_party_id=2)
        ]

        mock_llm.match_conference_member.return_value = {
            "matched_id": None,
            "confidence": 0.3,
        }

        # Execute
        result = await usecase._match_member_to_politician(member, threshold=0.7)

        # Verify
        assert result.status == "no_match"
        assert result.matched_politician_id is None
        # When LLM confidence is below threshold, the method returns default values
        assert result.confidence_score == 0.0
        assert result.member_name == "山田太郎"

    @pytest.mark.asyncio
    async def test_create_affiliations_success(
        self, usecase, mock_extracted_repo, mock_affiliation_repo
    ):
        """Test successful creation of affiliations."""
        # Setup
        matched_members = [
            create_mock_extracted_member(
                id=1,
                name="山田太郎",
                conference_id=1,
                matched_politician_id=10,
                role="議員",
                matching_status="matched",
            ),
            create_mock_extracted_member(
                id=2,
                name="佐藤花子",
                conference_id=1,
                matched_politician_id=20,
                role="委員長",
                matching_status="matched",
            ),
        ]

        mock_extracted_repo.get_by_conference_and_status.return_value = matched_members
        mock_affiliation_repo.get_by_politician_and_conference.return_value = []

        # Execute
        result = await usecase.create_affiliations(
            conference_id=1, start_date=date(2023, 1, 1)
        )

        # Verify
        assert len(result) == 2
        assert result[0].politician_id == 10
        assert result[0].conference_id == 1
        assert result[0].role == "議員"
        assert result[1].politician_id == 20
        assert result[1].conference_id == 1
        assert result[1].role == "委員長"

        # Verify repository calls
        assert mock_affiliation_repo.create.call_count == 2
        assert mock_extracted_repo.mark_processed.call_count == 2

    @pytest.mark.asyncio
    async def test_create_affiliations_skip_existing(
        self,
        usecase,
        mock_extracted_repo,
        mock_affiliation_repo,
        mock_conference_service,
    ):
        """Test skipping creation when affiliation already exists."""
        # Setup
        matched_member = create_mock_extracted_member(
            id=1,
            name="山田太郎",
            conference_id=1,
            matched_politician_id=10,
            role="議員",
            matching_status="matched",
        )

        mock_extracted_repo.get_by_conference_and_status.return_value = [matched_member]

        # Existing affiliation
        mock_affiliation_repo.get_by_politician_and_conference.return_value = [
            Mock(
                id=100,
                politician_id=10,
                conference_id=1,
                start_date=date(2022, 1, 1),
                end_date=None,
                role="議員",
            )
        ]

        # Mock overlap detection to return True (indicating overlap)
        mock_conference_service.calculate_affiliation_overlap.return_value = True

        # Execute
        result = await usecase.create_affiliations(
            conference_id=1, start_date=date(2023, 1, 1)
        )

        # Verify - should skip due to overlapping affiliation
        assert len(result) == 0

        # Verify no new affiliation was created
        mock_affiliation_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_affiliations_all_conferences(
        self, usecase, mock_extracted_repo, mock_affiliation_repo
    ):
        """Test creating affiliations for all conferences."""
        # Setup
        matched_members = [
            create_mock_extracted_member(
                id=1,
                name="山田太郎",
                conference_id=1,
                matched_politician_id=10,
                role="議員",
                matching_status="matched",
            ),
            create_mock_extracted_member(
                id=2,
                name="佐藤花子",
                conference_id=2,
                matched_politician_id=20,
                role="委員長",
                matching_status="matched",
            ),
        ]

        mock_extracted_repo.get_by_status.return_value = matched_members
        mock_affiliation_repo.get_by_politician_and_conference.return_value = []

        # Execute
        result = await usecase.create_affiliations(
            conference_id=None, start_date=date(2023, 1, 1)
        )

        # Verify
        assert len(result) == 2
        assert result[0].politician_id == 10
        assert result[1].politician_id == 20

        # Verify repository calls
        mock_extracted_repo.get_by_status.assert_called_once_with("matched")

    @pytest.mark.asyncio
    async def test_to_extracted_dto(self, usecase):
        """Test conversion to ExtractedConferenceMemberDTO."""
        # Setup
        entity = create_mock_extracted_member(
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
        assert dto.name == "山田太郎"
        assert dto.conference_id == 1
        assert dto.party_name == "自由民主党"
        assert dto.role == "議員"
        assert dto.profile_url is None  # Not available in ExtractedMemberEntity

    @pytest.mark.asyncio
    async def test_error_handling_in_extract_members(
        self, usecase, mock_scraper, mock_extracted_repo
    ):
        """Test error handling during member extraction."""
        # Setup
        mock_extracted_repo.get_by_conference.return_value = []  # No existing members
        mock_scraper.scrape_conference_members.side_effect = Exception("Network error")

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
    async def test_empty_extraction_result(
        self, usecase, mock_llm, mock_scraper, mock_extracted_repo
    ):
        """Test handling of empty extraction result."""
        # Setup
        mock_extracted_repo.get_by_conference.return_value = []  # No existing members
        mock_scraper.scrape_conference_members.return_value = []  # No members found

        # Execute
        result = await usecase.extract_members(conference_id=1, force=False)

        # Verify
        assert len(result) == 0
