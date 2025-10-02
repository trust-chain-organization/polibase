"""Tests for MatchParliamentaryGroupMembersUseCase."""

from unittest.mock import AsyncMock

import pytest

from src.application.usecases.match_parliamentary_group_members_usecase import (
    MatchParliamentaryGroupMembersUseCase,
)
from src.domain.entities.extracted_parliamentary_group_member import (
    ExtractedParliamentaryGroupMember,
)


class TestMatchParliamentaryGroupMembersUseCase:
    """Test cases for MatchParliamentaryGroupMembersUseCase."""

    @pytest.fixture
    def mock_member_repo(self):
        """Create mock member repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_matching_service(self):
        """Create mock matching service."""
        from unittest.mock import AsyncMock, MagicMock

        service = AsyncMock()
        # determine_matching_status is a synchronous method
        service.determine_matching_status = MagicMock()
        return service

    @pytest.fixture
    def use_case(self, mock_member_repo, mock_matching_service):
        """Create MatchParliamentaryGroupMembersUseCase instance."""
        return MatchParliamentaryGroupMembersUseCase(
            member_repository=mock_member_repo,
            matching_service=mock_matching_service,
        )

    @pytest.mark.asyncio
    async def test_execute_successful_matching(
        self, use_case, mock_member_repo, mock_matching_service
    ):
        """Test successful matching of members."""
        # Arrange
        member1 = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="田中太郎",
            source_url="http://example.com",
            id=1,
        )
        member2 = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="佐藤花子",
            source_url="http://example.com",
            id=2,
        )

        mock_member_repo.get_pending_members.return_value = [member1, member2]

        # Mock matching service responses
        mock_matching_service.find_matching_politician.side_effect = [
            (100, 0.9, "Matched with high confidence"),
            (200, 0.6, "Matched with medium confidence"),
        ]
        mock_matching_service.determine_matching_status.side_effect = [
            "matched",
            "needs_review",
        ]

        mock_member_repo.update_matching_result.return_value = None

        # Act
        results = await use_case.execute(parliamentary_group_id=1)

        # Assert
        assert len(results) == 2
        assert results[0]["member_name"] == "田中太郎"
        assert results[0]["matched_politician_id"] == 100
        assert results[0]["status"] == "matched"
        assert results[1]["member_name"] == "佐藤花子"
        assert results[1]["matched_politician_id"] == 200
        assert results[1]["status"] == "needs_review"

        # Verify repository calls
        assert mock_member_repo.update_matching_result.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_no_match(
        self, use_case, mock_member_repo, mock_matching_service
    ):
        """Test when no matching politician is found."""
        # Arrange
        member = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="Unknown Person",
            source_url="http://example.com",
            id=1,
        )

        mock_member_repo.get_pending_members.return_value = [member]
        mock_matching_service.find_matching_politician.return_value = (
            None,
            0.0,
            "No match found",
        )
        mock_matching_service.determine_matching_status.return_value = "no_match"

        # Act
        results = await use_case.execute(parliamentary_group_id=1)

        # Assert
        assert len(results) == 1
        assert results[0]["matched_politician_id"] is None
        assert results[0]["status"] == "no_match"

    @pytest.mark.asyncio
    async def test_execute_empty_pending_members(self, use_case, mock_member_repo):
        """Test when no pending members exist."""
        # Arrange
        mock_member_repo.get_pending_members.return_value = []

        # Act
        results = await use_case.execute(parliamentary_group_id=1)

        # Assert
        assert len(results) == 0
