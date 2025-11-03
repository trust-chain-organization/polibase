"""Tests for ParliamentaryGroupMemberMatchingService."""

from datetime import date
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.parliamentary_group_member_extractor.matching_service import (
    ParliamentaryGroupMemberMatchingService,
)


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return MagicMock()


@pytest.fixture
def mock_extracted_repo():
    """Create mock extracted member repository."""
    mock = MagicMock()
    mock.get_pending_members = MagicMock(return_value=[])
    mock.get_matched_members = MagicMock(return_value=[])
    mock.update_matching_result = MagicMock(return_value=True)
    mock.close = MagicMock()
    return mock


@pytest.fixture
def mock_politician_repo():
    """Create mock politician repository."""
    mock = MagicMock()
    mock.search_by_name_sync = MagicMock(return_value=[])
    mock.close = MagicMock()
    return mock


@pytest.fixture
def mock_membership_repo():
    """Create mock membership repository."""
    mock = MagicMock()
    mock.upsert_membership = MagicMock(return_value=1)
    mock.close = MagicMock()
    return mock


@pytest.fixture
def mock_llm_service():
    """Create mock LLM service."""
    mock = MagicMock()
    mock_response = Mock()
    mock_response.content = "番号: 1\n信頼度: 0.95\n理由: 名前と所属政党が完全に一致"
    mock.llm = MagicMock()
    mock.llm.invoke = MagicMock(return_value=mock_response)
    return mock


@pytest.fixture
def matching_service(
    mock_db_session,
    mock_extracted_repo,
    mock_politician_repo,
    mock_membership_repo,
    mock_llm_service,
):
    """Create matching service with mocked dependencies."""
    with (
        patch(
            "src.parliamentary_group_member_extractor.matching_service.RepositoryAdapter"
        ) as mock_adapter,
        patch(
            "src.parliamentary_group_member_extractor.matching_service.PoliticianRepositorySyncImpl"
        ) as mock_pol_impl,
        patch(
            "src.infrastructure.config.database.get_db_session",
            return_value=mock_db_session,
        ),
        patch(
            "src.parliamentary_group_member_extractor.matching_service.LLMService",
            return_value=mock_llm_service,
        ),
    ):
        # Setup repository adapter mock
        def adapter_side_effect(repo_class):
            if "ExtractedParliamentaryGroupMember" in repo_class.__name__:
                return mock_extracted_repo
            elif "ParliamentaryGroupMembership" in repo_class.__name__:
                return mock_membership_repo
            return MagicMock()

        mock_adapter.side_effect = adapter_side_effect
        mock_pol_impl.return_value = mock_politician_repo

        service = ParliamentaryGroupMemberMatchingService()
        service.extracted_repo = mock_extracted_repo
        service.politician_repo = mock_politician_repo
        service.membership_repo = mock_membership_repo
        service.llm_service = mock_llm_service

        return service


class TestParliamentaryGroupMemberMatchingServiceInit:
    """Test service initialization."""

    @patch(
        "src.parliamentary_group_member_extractor.matching_service.RepositoryAdapter"
    )
    @patch(
        "src.parliamentary_group_member_extractor.matching_service.PoliticianRepositorySyncImpl"
    )
    @patch("src.infrastructure.config.database.get_db_session")
    @patch("src.parliamentary_group_member_extractor.matching_service.LLMService")
    def test_init_creates_repositories(
        self, mock_llm_class, mock_session, mock_pol_impl, mock_adapter
    ):
        """Test initialization creates all necessary repositories."""
        ParliamentaryGroupMemberMatchingService()

        # Verify repositories were created
        assert mock_adapter.call_count >= 2  # extracted_repo and membership_repo
        assert mock_pol_impl.called
        assert mock_llm_class.called


class TestFindPoliticianCandidates:
    """Test find_politician_candidates method."""

    def test_find_with_exact_name_match(self, matching_service, mock_politician_repo):
        """Test finding candidates with exact name match."""
        mock_politician_repo.search_by_name_sync.return_value = [
            {"id": 1, "name": "山田太郎", "party_name": "政党A"},
            {"id": 2, "name": "山田太郎", "party_name": "政党B"},
        ]

        candidates = matching_service.find_politician_candidates("山田太郎", None)

        # Should return exact matches
        assert len(candidates) == 2
        assert all(c["name"] == "山田太郎" for c in candidates)

    def test_find_with_exact_name_and_party_match(
        self, matching_service, mock_politician_repo
    ):
        """Test finding candidates with exact name and party match."""
        mock_politician_repo.search_by_name_sync.return_value = [
            {"id": 1, "name": "山田太郎", "party_name": "政党A"},
            {"id": 2, "name": "山田太郎", "party_name": "政党B"},
        ]

        candidates = matching_service.find_politician_candidates("山田太郎", "政党A")

        # Should return only party match
        assert len(candidates) == 1
        assert candidates[0]["party_name"] == "政党A"

    def test_find_with_partial_match(self, matching_service, mock_politician_repo):
        """Test finding candidates with partial name match."""
        mock_politician_repo.search_by_name_sync.return_value = [
            {"id": 1, "name": "山田太郎", "party_name": "政党A"},
            {"id": 2, "name": "山田花子", "party_name": "政党B"},
            {"id": 3, "name": "山田次郎", "party_name": "政党C"},
        ]

        candidates = matching_service.find_politician_candidates("山田", None)

        # Should return partial matches (max 5)
        assert len(candidates) == 3

    def test_find_limits_to_five_candidates(
        self, matching_service, mock_politician_repo
    ):
        """Test finding candidates limits results to 5."""
        # Create 10 candidates
        mock_politician_repo.search_by_name_sync.return_value = [
            {"id": i, "name": f"山田{i}", "party_name": f"政党{i}"} for i in range(10)
        ]

        candidates = matching_service.find_politician_candidates("山田", None)

        # Should limit to 5
        assert len(candidates) == 5

    def test_find_with_no_matches(self, matching_service, mock_politician_repo):
        """Test finding candidates with no matches."""
        mock_politician_repo.search_by_name_sync.return_value = []

        candidates = matching_service.find_politician_candidates("存在しない", None)

        assert len(candidates) == 0


class TestMatchWithLLM:
    """Test match_with_llm method."""

    def test_match_with_no_candidates(self, matching_service):
        """Test matching with no candidates returns None."""
        extracted_member = {"extracted_name": "山田太郎"}

        politician_id, confidence = matching_service.match_with_llm(
            extracted_member, []
        )

        assert politician_id is None
        assert confidence == 0.0

    def test_match_with_single_candidate_same_party(self, matching_service):
        """Test matching with single candidate and matching party."""
        extracted_member = {
            "extracted_name": "山田太郎",
            "extracted_party_name": "政党A",
        }
        candidates = [{"id": 1, "name": "山田太郎", "party_name": "政党A"}]

        politician_id, confidence = matching_service.match_with_llm(
            extracted_member, candidates
        )

        # Should return high confidence match
        assert politician_id == 1
        assert confidence == 0.95

    def test_match_with_single_candidate_different_party(self, matching_service):
        """Test matching with single candidate and different party."""
        extracted_member = {
            "extracted_name": "山田太郎",
            "extracted_party_name": "政党A",
        }
        candidates = [{"id": 1, "name": "山田太郎", "party_name": "政党B"}]

        politician_id, confidence = matching_service.match_with_llm(
            extracted_member, candidates
        )

        # Should return medium confidence match
        assert politician_id == 1
        assert confidence == 0.85

    def test_match_with_multiple_candidates_uses_llm(
        self, matching_service, mock_llm_service
    ):
        """Test matching with multiple candidates uses LLM."""
        extracted_member = {
            "extracted_name": "山田太郎",
            "extracted_party_name": "政党A",
            "extracted_role": "委員長",
            "group_name": "会派A",
        }
        candidates = [
            {"id": 1, "name": "山田太郎", "party_name": "政党A"},
            {"id": 2, "name": "山田太郎", "party_name": "政党B"},
        ]

        politician_id, confidence = matching_service.match_with_llm(
            extracted_member, candidates
        )

        # Should use LLM to decide
        assert mock_llm_service.llm.invoke.called
        assert politician_id == 1  # Based on mock response "番号: 1"
        assert confidence == 0.95  # Based on mock response "信頼度: 0.95"

    def test_match_with_llm_error_returns_none(
        self, matching_service, mock_llm_service
    ):
        """Test matching handles LLM errors gracefully."""
        extracted_member = {"extracted_name": "山田太郎"}
        candidates = [
            {"id": 1, "name": "山田太郎", "party_name": "政党A"},
            {"id": 2, "name": "山田太郎", "party_name": "政党B"},
        ]
        mock_llm_service.llm.invoke.side_effect = Exception("LLM error")

        politician_id, confidence = matching_service.match_with_llm(
            extracted_member, candidates
        )

        assert politician_id is None
        assert confidence == 0.0

    def test_match_with_llm_invalid_response_format(
        self, matching_service, mock_llm_service
    ):
        """Test matching handles invalid LLM response format."""
        mock_response = Mock()
        mock_response.content = "Invalid format"
        mock_llm_service.llm.invoke.return_value = mock_response

        extracted_member = {"extracted_name": "山田太郎"}
        candidates = [{"id": 1, "name": "山田太郎", "party_name": "政党A"}]

        politician_id, confidence = matching_service.match_with_llm(
            extracted_member, candidates
        )

        # Should handle invalid format gracefully
        assert politician_id is None or confidence == 0.0

    def test_match_with_llm_out_of_range_selection(
        self, matching_service, mock_llm_service
    ):
        """Test matching handles out-of-range candidate selection."""
        mock_response = Mock()
        mock_response.content = "番号: 99\n信頼度: 0.95\n理由: テスト"
        mock_llm_service.llm.invoke.return_value = mock_response

        extracted_member = {"extracted_name": "山田太郎"}
        candidates = [{"id": 1, "name": "山田太郎", "party_name": "政党A"}]

        politician_id, confidence = matching_service.match_with_llm(
            extracted_member, candidates
        )

        assert politician_id is None
        assert confidence == 0.0

    def test_match_with_llm_zero_selection(self, matching_service, mock_llm_service):
        """Test matching handles zero (no match) selection."""
        mock_response = Mock()
        mock_response.content = "番号: 0\n信頼度: 0.0\n理由: 該当なし"
        mock_llm_service.llm.invoke.return_value = mock_response

        extracted_member = {"extracted_name": "山田太郎"}
        candidates = [{"id": 1, "name": "山田太郎", "party_name": "政党A"}]

        politician_id, confidence = matching_service.match_with_llm(
            extracted_member, candidates
        )

        assert politician_id is None
        assert confidence == 0.0


class TestProcessExtractedMember:
    """Test process_extracted_member method."""

    def test_process_member_with_no_candidates(
        self, matching_service, mock_politician_repo, mock_extracted_repo
    ):
        """Test processing member with no candidates."""
        mock_politician_repo.search_by_name_sync.return_value = []
        extracted_member = {"id": 1, "extracted_name": "山田太郎"}

        result = matching_service.process_extracted_member(extracted_member)

        assert result["status"] == "no_match"
        assert result["politician_id"] is None
        assert result["confidence"] == 0.0
        mock_extracted_repo.update_matching_result.assert_called_with(
            member_id=1, politician_id=None, confidence=0.0, status="no_match"
        )

    def test_process_member_with_high_confidence_match(
        self, matching_service, mock_politician_repo, mock_extracted_repo
    ):
        """Test processing member with high confidence match."""
        mock_politician_repo.search_by_name_sync.return_value = [
            {"id": 10, "name": "山田太郎", "party_name": "政党A"}
        ]
        extracted_member = {
            "id": 1,
            "extracted_name": "山田太郎",
            "extracted_party_name": "政党A",
        }

        result = matching_service.process_extracted_member(extracted_member)

        assert result["status"] == "matched"
        assert result["politician_id"] == 10
        assert result["confidence"] >= 0.7
        mock_extracted_repo.update_matching_result.assert_called_with(
            member_id=1, politician_id=10, confidence=0.95, status="matched"
        )

    def test_process_member_with_medium_confidence(
        self,
        matching_service,
        mock_politician_repo,
        mock_llm_service,
        mock_extracted_repo,
    ):
        """Test processing member with medium confidence (needs review)."""
        mock_politician_repo.search_by_name_sync.return_value = [
            {"id": 10, "name": "山田太郎", "party_name": "政党A"},
            {"id": 11, "name": "山田太郎", "party_name": "政党B"},
        ]
        # Set LLM to return medium confidence
        mock_response = Mock()
        mock_response.content = "番号: 1\n信頼度: 0.6\n理由: 中程度の一致"
        mock_llm_service.llm.invoke.return_value = mock_response

        extracted_member = {"id": 1, "extracted_name": "山田太郎"}

        result = matching_service.process_extracted_member(extracted_member)

        assert result["status"] == "needs_review"
        assert result["confidence"] >= 0.5
        assert result["confidence"] < 0.7

    def test_process_member_with_low_confidence(
        self,
        matching_service,
        mock_politician_repo,
        mock_llm_service,
        mock_extracted_repo,
    ):
        """Test processing member with low confidence."""
        mock_politician_repo.search_by_name_sync.return_value = [
            {"id": 10, "name": "田中太郎", "party_name": "政党A"}
        ]
        # Set LLM to return low confidence
        mock_response = Mock()
        mock_response.content = "番号: 1\n信頼度: 0.3\n理由: 低い一致"
        mock_llm_service.llm.invoke.return_value = mock_response

        extracted_member = {"id": 1, "extracted_name": "山田太郎"}

        result = matching_service.process_extracted_member(extracted_member)

        assert result["status"] == "no_match"

    def test_process_member_handles_exception(
        self, matching_service, mock_politician_repo
    ):
        """Test processing member handles exceptions."""
        mock_politician_repo.search_by_name_sync.side_effect = Exception("DB error")
        extracted_member = {"id": 1, "extracted_name": "山田太郎"}

        result = matching_service.process_extracted_member(extracted_member)

        assert result["status"] == "error"
        assert "error" in result


class TestProcessPendingMembers:
    """Test process_pending_members method."""

    def test_process_pending_members_empty(self, matching_service, mock_extracted_repo):
        """Test processing with no pending members."""
        mock_extracted_repo.get_pending_members.return_value = []

        results = matching_service.process_pending_members()

        assert results["total"] == 0
        assert results["matched"] == 0
        assert results["no_match"] == 0
        assert results["needs_review"] == 0

    def test_process_pending_members_with_matches(
        self, matching_service, mock_extracted_repo, mock_politician_repo
    ):
        """Test processing pending members with matches."""
        # Create mock member entities
        mock_member = Mock()
        mock_member.id = 1
        mock_member.extracted_name = "山田太郎"
        mock_member.extracted_party_name = "政党A"
        mock_member.extracted_role = "委員長"

        mock_extracted_repo.get_pending_members.return_value = [mock_member]
        mock_politician_repo.search_by_name_sync.return_value = [
            {"id": 10, "name": "山田太郎", "party_name": "政党A"}
        ]

        results = matching_service.process_pending_members()

        assert results["total"] == 1
        assert results["matched"] == 1

    def test_process_pending_members_with_no_matches(
        self, matching_service, mock_extracted_repo, mock_politician_repo
    ):
        """Test processing pending members with no matches."""
        mock_member = Mock()
        mock_member.id = 1
        mock_member.extracted_name = "山田太郎"
        mock_member.extracted_party_name = None
        mock_member.extracted_role = None

        mock_extracted_repo.get_pending_members.return_value = [mock_member]
        mock_politician_repo.search_by_name_sync.return_value = []

        results = matching_service.process_pending_members()

        assert results["total"] == 1
        assert results["no_match"] == 1

    def test_process_pending_members_filters_by_group(
        self, matching_service, mock_extracted_repo
    ):
        """Test processing filters by parliamentary group."""
        matching_service.process_pending_members(parliamentary_group_id=5)

        mock_extracted_repo.get_pending_members.assert_called_with(5)

    def test_process_pending_members_handles_errors(
        self, matching_service, mock_extracted_repo, mock_politician_repo
    ):
        """Test processing handles errors in individual members."""
        mock_member = Mock()
        mock_member.id = 1
        mock_member.extracted_name = "山田太郎"
        mock_member.extracted_party_name = None
        mock_member.extracted_role = None

        mock_extracted_repo.get_pending_members.return_value = [mock_member]
        mock_politician_repo.search_by_name_sync.side_effect = Exception("Error")

        results = matching_service.process_pending_members()

        assert results["total"] == 1
        assert results["error"] == 1


class TestCreateMembershipsFromMatched:
    """Test create_memberships_from_matched method."""

    def test_create_memberships_with_no_matched(
        self, matching_service, mock_extracted_repo
    ):
        """Test creating memberships with no matched members."""
        mock_extracted_repo.get_matched_members.return_value = []

        results = matching_service.create_memberships_from_matched()

        assert results["total"] == 0
        assert results["created"] == 0

    def test_create_memberships_with_matched_members(
        self, matching_service, mock_extracted_repo, mock_membership_repo
    ):
        """Test creating memberships for matched members."""
        mock_member = Mock()
        mock_member.id = 1
        mock_member.matched_politician_id = 10
        mock_member.parliamentary_group_id = 5
        mock_member.extracted_role = "委員長"

        mock_extracted_repo.get_matched_members.return_value = [mock_member]
        mock_membership_repo.upsert_membership.return_value = 100

        results = matching_service.create_memberships_from_matched()

        assert results["total"] == 1
        assert results["created"] == 1
        mock_membership_repo.upsert_membership.assert_called_once()

    def test_create_memberships_with_custom_start_date(
        self, matching_service, mock_extracted_repo, mock_membership_repo
    ):
        """Test creating memberships with custom start date."""
        mock_member = Mock()
        mock_member.id = 1
        mock_member.matched_politician_id = 10
        mock_member.parliamentary_group_id = 5
        mock_member.extracted_role = "委員長"

        mock_extracted_repo.get_matched_members.return_value = [mock_member]

        start_date = date(2024, 1, 1)
        matching_service.create_memberships_from_matched(start_date=start_date)

        # Verify start_date was passed
        call_args = mock_membership_repo.upsert_membership.call_args
        assert call_args[1]["start_date"] == start_date

    def test_create_memberships_filters_by_group(
        self, matching_service, mock_extracted_repo
    ):
        """Test creating memberships filters by parliamentary group."""
        matching_service.create_memberships_from_matched(parliamentary_group_id=5)

        mock_extracted_repo.get_matched_members.assert_called_with(5)

    def test_create_memberships_handles_failures(
        self, matching_service, mock_extracted_repo, mock_membership_repo
    ):
        """Test creating memberships handles failures."""
        mock_member = Mock()
        mock_member.id = 1
        mock_member.matched_politician_id = 10
        mock_member.parliamentary_group_id = 5
        mock_member.extracted_role = "委員長"

        mock_extracted_repo.get_matched_members.return_value = [mock_member]
        mock_membership_repo.upsert_membership.side_effect = Exception("DB error")

        results = matching_service.create_memberships_from_matched()

        assert results["total"] == 1
        assert results["failed"] == 1

    def test_create_memberships_handles_null_return(
        self, matching_service, mock_extracted_repo, mock_membership_repo
    ):
        """Test creating memberships handles null return from upsert."""
        mock_member = Mock()
        mock_member.id = 1
        mock_member.matched_politician_id = 10
        mock_member.parliamentary_group_id = 5
        mock_member.extracted_role = "委員長"

        mock_extracted_repo.get_matched_members.return_value = [mock_member]
        mock_membership_repo.upsert_membership.return_value = None

        results = matching_service.create_memberships_from_matched()

        assert results["total"] == 1
        assert results["failed"] == 1


class TestClose:
    """Test close method."""

    def test_close_closes_all_repositories(
        self,
        matching_service,
        mock_extracted_repo,
        mock_politician_repo,
        mock_membership_repo,
    ):
        """Test close closes all repositories."""
        matching_service.close()

        mock_extracted_repo.close.assert_called_once()
        mock_politician_repo.close.assert_called_once()
        mock_membership_repo.close.assert_called_once()
