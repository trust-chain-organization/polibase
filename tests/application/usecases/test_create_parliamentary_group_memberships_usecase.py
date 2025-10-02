"""Tests for CreateParliamentaryGroupMembershipsUseCase."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.application.usecases.create_parliamentary_group_memberships_usecase import (
    CreateParliamentaryGroupMembershipsUseCase,
)
from src.domain.entities.extracted_parliamentary_group_member import (
    ExtractedParliamentaryGroupMember,
)


class TestCreateParliamentaryGroupMembershipsUseCase:
    """Test cases for CreateParliamentaryGroupMembershipsUseCase."""

    @pytest.fixture
    def mock_member_repo(self):
        """Create mock member repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_membership_repo(self):
        """Create mock membership repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def use_case(self, mock_member_repo, mock_membership_repo):
        """Create CreateParliamentaryGroupMembershipsUseCase instance."""
        return CreateParliamentaryGroupMembershipsUseCase(
            member_repository=mock_member_repo,
            membership_repository=mock_membership_repo,
        )

    @pytest.mark.asyncio
    async def test_execute_successful_creation(
        self, use_case, mock_member_repo, mock_membership_repo
    ):
        """Test successful creation of memberships."""
        from datetime import date

        from src.domain.entities.parliamentary_group_membership import (
            ParliamentaryGroupMembership,
        )

        # Arrange
        member1 = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="田中太郎",
            source_url="http://example.com",
            matched_politician_id=100,
            matching_confidence=0.9,
            matching_status="matched",
            extracted_role="団長",
            id=1,
        )
        member2 = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="佐藤花子",
            source_url="http://example.com",
            matched_politician_id=200,
            matching_confidence=0.85,
            matching_status="matched",
            extracted_role="幹事長",
            id=2,
        )

        mock_member_repo.get_matched_members.return_value = [member1, member2]
        mock_membership_repo.create_membership.side_effect = [
            ParliamentaryGroupMembership(
                id=1,
                politician_id=100,
                parliamentary_group_id=1,
                start_date=date.today(),
                role="団長",
            ),
            ParliamentaryGroupMembership(
                id=2,
                politician_id=200,
                parliamentary_group_id=1,
                start_date=date.today(),
                role="幹事長",
            ),
        ]

        # Act
        result = await use_case.execute(parliamentary_group_id=1)

        # Assert
        assert result["created_count"] == 2
        assert result["skipped_count"] == 0
        assert len(result["created_memberships"]) == 2
        assert result["created_memberships"][0]["politician_id"] == 100
        assert result["created_memberships"][0]["role"] == "団長"
        assert result["created_memberships"][1]["politician_id"] == 200
        assert result["created_memberships"][1]["role"] == "幹事長"

    @pytest.mark.asyncio
    async def test_execute_skip_members_without_politician_id(
        self, use_case, mock_member_repo
    ):
        """Test skipping members without matched_politician_id."""
        # Arrange
        member1 = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="田中太郎",
            source_url="http://example.com",
            matched_politician_id=None,  # No match
            matching_confidence=0.3,
            matching_status="no_match",
            id=1,
        )

        mock_member_repo.get_matched_members.return_value = [member1]

        # Act
        result = await use_case.execute(parliamentary_group_id=1)

        # Assert
        assert result["created_count"] == 0
        assert result["skipped_count"] == 1

    @pytest.mark.asyncio
    async def test_execute_with_custom_start_date(
        self, use_case, mock_member_repo, mock_membership_repo
    ):
        """Test creation with custom start date."""
        from src.domain.entities.parliamentary_group_membership import (
            ParliamentaryGroupMembership,
        )

        # Arrange
        custom_date = date(2024, 1, 1)
        member = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="田中太郎",
            source_url="http://example.com",
            matched_politician_id=100,
            matching_confidence=0.9,
            matching_status="matched",
            id=1,
        )

        mock_member_repo.get_matched_members.return_value = [member]
        mock_membership_repo.create_membership.return_value = (
            ParliamentaryGroupMembership(
                id=1,
                politician_id=100,
                parliamentary_group_id=1,
                start_date=custom_date,
            )
        )

        # Act
        await use_case.execute(parliamentary_group_id=1, start_date=custom_date)

        # Assert
        mock_membership_repo.create_membership.assert_called_once()
        call_args = mock_membership_repo.create_membership.call_args
        assert call_args.kwargs["start_date"] == custom_date

    @pytest.mark.asyncio
    async def test_execute_handle_creation_error(
        self, use_case, mock_member_repo, mock_membership_repo, capsys
    ):
        """Test handling of membership creation errors."""
        # Arrange
        member = ExtractedParliamentaryGroupMember(
            parliamentary_group_id=1,
            extracted_name="田中太郎",
            source_url="http://example.com",
            matched_politician_id=100,
            matching_confidence=0.9,
            matching_status="matched",
            id=1,
        )

        mock_member_repo.get_matched_members.return_value = [member]
        mock_membership_repo.create_membership.side_effect = Exception("DB Error")

        # Act
        result = await use_case.execute(parliamentary_group_id=1)

        # Assert
        assert result["created_count"] == 0
        assert result["skipped_count"] == 1
