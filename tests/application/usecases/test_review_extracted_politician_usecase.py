"""Tests for ReviewExtractedPoliticianUseCase."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dtos.review_extracted_politician_dto import (
    BulkReviewInputDTO,
    ExtractedPoliticianFilterDTO,
    ReviewExtractedPoliticianInputDTO,
)
from src.application.usecases.review_extracted_politician_usecase import (
    ReviewExtractedPoliticianUseCase,
)
from src.domain.entities.political_party import PoliticalParty
from src.domain.entities.politician_party_extracted_politician import (
    PoliticianPartyExtractedPolitician,
)


class TestReviewExtractedPoliticianUseCase:
    """Test class for ReviewExtractedPoliticianUseCase."""

    @pytest.fixture
    def mock_extracted_politician_repo(self):
        """Create a mock extracted politician repository."""
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock()
        mock_repo.update_status = AsyncMock()
        mock_repo.get_all = AsyncMock()
        mock_repo.get_summary_by_status = AsyncMock()
        mock_repo.get_statistics_by_party = AsyncMock()
        return mock_repo

    @pytest.fixture
    def mock_party_repo(self):
        """Create a mock party repository."""
        mock_repo = MagicMock()
        mock_repo.get_all = AsyncMock()
        return mock_repo

    @pytest.fixture
    def use_case(self, mock_extracted_politician_repo, mock_party_repo):
        """Create a use case instance with mocked dependencies."""
        return ReviewExtractedPoliticianUseCase(
            mock_extracted_politician_repo, mock_party_repo
        )

    @pytest.fixture
    def sample_extracted_politician(self):
        """Create a sample extracted politician."""
        return PoliticianPartyExtractedPolitician(
            id=1,
            name="山田太郎",
            party_id=1,
            district="東京1区",
            profile_url="https://example.com/profile",
            status="pending",
            extracted_at=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_review_politician_approve_success(
        self, use_case, mock_extracted_politician_repo, sample_extracted_politician
    ):
        """Test successful approval of a politician."""
        # Arrange
        mock_extracted_politician_repo.get_by_id.return_value = (
            sample_extracted_politician
        )
        updated_politician = sample_extracted_politician
        updated_politician.status = "approved"
        mock_extracted_politician_repo.update_status.return_value = updated_politician

        request = ReviewExtractedPoliticianInputDTO(
            politician_id=1, action="approve", reviewer_id=1
        )

        # Act
        result = await use_case.review_politician(request)

        # Assert
        assert result.success is True
        assert result.politician_id == 1
        assert result.name == "山田太郎"
        assert result.new_status == "approved"
        assert "Successfully approved" in result.message

    @pytest.mark.asyncio
    async def test_review_politician_reject_success(
        self, use_case, mock_extracted_politician_repo, sample_extracted_politician
    ):
        """Test successful rejection of a politician."""
        # Arrange
        mock_extracted_politician_repo.get_by_id.return_value = (
            sample_extracted_politician
        )
        updated_politician = sample_extracted_politician
        updated_politician.status = "rejected"
        mock_extracted_politician_repo.update_status.return_value = updated_politician

        request = ReviewExtractedPoliticianInputDTO(
            politician_id=1, action="reject", reviewer_id=1
        )

        # Act
        result = await use_case.review_politician(request)

        # Assert
        assert result.success is True
        assert result.new_status == "rejected"
        assert "Successfully rejected" in result.message

    @pytest.mark.asyncio
    async def test_review_politician_not_found(
        self, use_case, mock_extracted_politician_repo
    ):
        """Test review of non-existent politician."""
        # Arrange
        mock_extracted_politician_repo.get_by_id.return_value = None
        request = ReviewExtractedPoliticianInputDTO(
            politician_id=999, action="approve", reviewer_id=1
        )

        # Act
        result = await use_case.review_politician(request)

        # Assert
        assert result.success is False
        assert "not found" in result.message

    @pytest.mark.asyncio
    async def test_review_politician_invalid_action(
        self, use_case, mock_extracted_politician_repo, sample_extracted_politician
    ):
        """Test review with invalid action."""
        # Arrange
        mock_extracted_politician_repo.get_by_id.return_value = (
            sample_extracted_politician
        )
        request = ReviewExtractedPoliticianInputDTO(
            politician_id=1, action="invalid_action", reviewer_id=1
        )

        # Act
        result = await use_case.review_politician(request)

        # Assert
        assert result.success is False
        assert "Invalid action" in result.message

    @pytest.mark.asyncio
    async def test_bulk_review_success(
        self, use_case, mock_extracted_politician_repo, sample_extracted_politician
    ):
        """Test successful bulk review."""
        # Arrange
        mock_extracted_politician_repo.get_by_id.return_value = (
            sample_extracted_politician
        )
        updated_politician = sample_extracted_politician
        updated_politician.status = "approved"
        mock_extracted_politician_repo.update_status.return_value = updated_politician

        request = BulkReviewInputDTO(
            politician_ids=[1, 2, 3], action="approve", reviewer_id=1
        )

        # Act
        result = await use_case.bulk_review(request)

        # Assert
        assert result.total_processed == 3
        assert result.successful_count == 3
        assert result.failed_count == 0
        assert "Processed 3 politicians" in result.message

    @pytest.mark.asyncio
    async def test_get_filtered_politicians(
        self, use_case, mock_extracted_politician_repo
    ):
        """Test getting filtered politicians."""
        # Arrange
        expected_politician = PoliticianPartyExtractedPolitician(
            id=1,
            name="山田太郎",
            party_id=1,
            status="pending",
            extracted_at=datetime.now(),
        )

        # Mock async method
        async def mock_get_filtered(*args, **kwargs):
            return [expected_politician]

        mock_extracted_politician_repo.get_filtered = mock_get_filtered

        filter_dto = ExtractedPoliticianFilterDTO(
            statuses=["pending"], party_id=1, search_name="山田"
        )

        # Act
        result = await use_case.get_filtered_politicians(filter_dto)

        # Assert
        assert len(result) == 1
        assert result[0].name == "山田太郎"

    @pytest.mark.asyncio
    async def test_get_statistics(
        self, use_case, mock_extracted_politician_repo, mock_party_repo
    ):
        """Test getting statistics."""
        # Arrange
        mock_extracted_politician_repo.get_summary_by_status.return_value = {
            "pending": 10,
            "approved": 5,
            "rejected": 2,
            "reviewed": 3,
            "converted": 8,
        }

        parties = [
            PoliticalParty(id=1, name="政党A"),
            PoliticalParty(id=2, name="政党B"),
        ]
        mock_party_repo.get_all.return_value = parties

        mock_extracted_politician_repo.get_statistics_by_party.side_effect = [
            {
                "total": 15,
                "pending": 8,
                "approved": 3,
                "rejected": 1,
                "reviewed": 2,
                "converted": 1,
            },
            {
                "total": 13,
                "pending": 2,
                "approved": 2,
                "rejected": 1,
                "reviewed": 1,
                "converted": 7,
            },
        ]

        # Act
        result = await use_case.get_statistics()

        # Assert
        assert result.total == 28
        assert result.pending_count == 10
        assert result.approved_count == 5
        assert result.rejected_count == 2
        assert result.reviewed_count == 3
        assert result.converted_count == 8
        assert len(result.party_statistics) == 2
        assert "政党A" in result.party_statistics
        assert result.party_statistics["政党A"]["total"] == 15
