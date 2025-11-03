"""Tests for data coverage domain service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.services.data_coverage_domain_service import DataCoverageDomainService


class TestDataCoverageDomainService:
    """Test cases for DataCoverageDomainService."""

    @pytest.fixture
    def mock_repos(self):
        """Create mock repositories."""
        return {
            "governing_body_repo": MagicMock(),
            "conference_repo": MagicMock(),
            "meeting_repo": MagicMock(),
            "minutes_repo": MagicMock(),
            "speaker_repo": MagicMock(),
            "politician_repo": MagicMock(),
            "conversation_repo": MagicMock(),
        }

    @pytest.fixture
    def service(self, mock_repos):
        """Create service instance with mocked repositories."""
        return DataCoverageDomainService(**mock_repos)

    @pytest.mark.asyncio
    async def test_calculate_governing_body_coverage_full_coverage(
        self, service, mock_repos
    ):
        """Test governing body coverage calculation with full coverage."""
        # Setup: All 1,966 municipalities registered
        mock_repos["governing_body_repo"].count = AsyncMock(return_value=1966)

        result = await service.calculate_governing_body_coverage()

        assert result["total"] == 1966
        assert result["registered"] == 1966
        assert result["coverage_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_calculate_governing_body_coverage_partial(self, service, mock_repos):
        """Test governing body coverage calculation with partial coverage."""
        # Setup: Only 500 municipalities registered
        mock_repos["governing_body_repo"].count = AsyncMock(return_value=500)

        result = await service.calculate_governing_body_coverage()

        assert result["total"] == 1966
        assert result["registered"] == 500
        # 500/1966 * 100 ≈ 25.43
        assert result["coverage_rate"] == 25.43

    @pytest.mark.asyncio
    async def test_calculate_governing_body_coverage_zero(self, service, mock_repos):
        """Test governing body coverage calculation with zero registered."""
        # Setup: No municipalities registered
        mock_repos["governing_body_repo"].count = AsyncMock(return_value=0)

        result = await service.calculate_governing_body_coverage()

        assert result["total"] == 1966
        assert result["registered"] == 0
        assert result["coverage_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_calculate_meeting_coverage_full(self, service, mock_repos):
        """Test meeting coverage calculation with full coverage."""
        # Setup: All 100 bodies have conferences and meetings
        mock_repos["governing_body_repo"].count = AsyncMock(return_value=100)
        mock_repos["governing_body_repo"].count_with_conferences = AsyncMock(
            return_value=100
        )
        mock_repos["governing_body_repo"].count_with_meetings = AsyncMock(
            return_value=100
        )

        result = await service.calculate_meeting_coverage()

        assert result["total_governing_bodies"] == 100
        assert result["bodies_with_conferences"] == 100
        assert result["bodies_with_meetings"] == 100
        assert result["conference_coverage_rate"] == 100.0
        assert result["meeting_coverage_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_calculate_meeting_coverage_partial(self, service, mock_repos):
        """Test meeting coverage calculation with partial coverage."""
        # Setup: 100 total, 60 with conferences, 40 with meetings
        mock_repos["governing_body_repo"].count = AsyncMock(return_value=100)
        mock_repos["governing_body_repo"].count_with_conferences = AsyncMock(
            return_value=60
        )
        mock_repos["governing_body_repo"].count_with_meetings = AsyncMock(
            return_value=40
        )

        result = await service.calculate_meeting_coverage()

        assert result["total_governing_bodies"] == 100
        assert result["bodies_with_conferences"] == 60
        assert result["bodies_with_meetings"] == 40
        assert result["conference_coverage_rate"] == 60.0
        assert result["meeting_coverage_rate"] == 40.0

    @pytest.mark.asyncio
    async def test_calculate_meeting_coverage_zero_bodies(self, service, mock_repos):
        """Test meeting coverage calculation with zero governing bodies."""
        # Setup: No governing bodies registered
        mock_repos["governing_body_repo"].count = AsyncMock(return_value=0)
        mock_repos["governing_body_repo"].count_with_conferences = AsyncMock(
            return_value=0
        )
        mock_repos["governing_body_repo"].count_with_meetings = AsyncMock(
            return_value=0
        )

        result = await service.calculate_meeting_coverage()

        assert result["total_governing_bodies"] == 0
        assert result["bodies_with_conferences"] == 0
        assert result["bodies_with_meetings"] == 0
        # Edge case: should not divide by zero
        assert result["conference_coverage_rate"] == 0.0
        assert result["meeting_coverage_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_calculate_speaker_matching_rate_full(self, service, mock_repos):
        """Test speaker matching rate calculation with full matching."""
        # Setup: All speakers are linked
        mock_repos["speaker_repo"].get_speaker_politician_stats = AsyncMock(
            return_value={
                "total_speakers": 1000,
                "linked_speakers": 1000,
                "politician_speakers": 800,
                "linked_politician_speakers": 800,
            }
        )

        result = await service.calculate_speaker_matching_rate()

        assert result["total_speakers"] == 1000
        assert result["linked_speakers"] == 1000
        assert result["unlinked_speakers"] == 0
        assert result["overall_matching_rate"] == 100.0
        assert result["politician_speakers"] == 800
        assert result["linked_politician_speakers"] == 800
        assert result["unlinked_politician_speakers"] == 0
        assert result["politician_matching_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_calculate_speaker_matching_rate_partial(self, service, mock_repos):
        """Test speaker matching rate calculation with partial matching."""
        # Setup: Partial matching (70% overall, 80% for politician speakers)
        mock_repos["speaker_repo"].get_speaker_politician_stats = AsyncMock(
            return_value={
                "total_speakers": 1000,
                "linked_speakers": 700,
                "politician_speakers": 800,
                "linked_politician_speakers": 640,
            }
        )

        result = await service.calculate_speaker_matching_rate()

        assert result["total_speakers"] == 1000
        assert result["linked_speakers"] == 700
        assert result["unlinked_speakers"] == 300
        assert result["overall_matching_rate"] == 70.0
        assert result["politician_speakers"] == 800
        assert result["linked_politician_speakers"] == 640
        assert result["unlinked_politician_speakers"] == 160
        assert result["politician_matching_rate"] == 80.0

    @pytest.mark.asyncio
    async def test_calculate_speaker_matching_rate_zero_speakers(
        self, service, mock_repos
    ):
        """Test speaker matching rate calculation with zero speakers."""
        # Setup: No speakers
        mock_repos["speaker_repo"].get_speaker_politician_stats = AsyncMock(
            return_value={
                "total_speakers": 0,
                "linked_speakers": 0,
                "politician_speakers": 0,
                "linked_politician_speakers": 0,
            }
        )

        result = await service.calculate_speaker_matching_rate()

        assert result["total_speakers"] == 0
        assert result["linked_speakers"] == 0
        assert result["unlinked_speakers"] == 0
        # Edge case: should not divide by zero
        assert result["overall_matching_rate"] == 0.0
        assert result["politician_speakers"] == 0
        assert result["linked_politician_speakers"] == 0
        assert result["unlinked_politician_speakers"] == 0
        assert result["politician_matching_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_calculate_speaker_matching_rate_no_politician_speakers(
        self, service, mock_repos
    ):
        """Test speaker matching rate with no politician speakers."""
        # Setup: Has speakers but none are politicians
        mock_repos["speaker_repo"].get_speaker_politician_stats = AsyncMock(
            return_value={
                "total_speakers": 500,
                "linked_speakers": 0,
                "politician_speakers": 0,
                "linked_politician_speakers": 0,
            }
        )

        result = await service.calculate_speaker_matching_rate()

        assert result["total_speakers"] == 500
        assert result["linked_speakers"] == 0
        assert result["unlinked_speakers"] == 500
        assert result["overall_matching_rate"] == 0.0
        assert result["politician_speakers"] == 0
        assert result["linked_politician_speakers"] == 0
        assert result["unlinked_politician_speakers"] == 0
        # Edge case: should not divide by zero
        assert result["politician_matching_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_aggregate_activity_statistics_full(self, service, mock_repos):
        """Test activity statistics aggregation with data."""
        # Setup: Various activity metrics
        mock_repos["meeting_repo"].count = AsyncMock(return_value=500)
        mock_repos["minutes_repo"].count = AsyncMock(return_value=450)
        mock_repos["minutes_repo"].count_processed = AsyncMock(return_value=360)
        mock_repos["conversation_repo"].count = AsyncMock(return_value=5000)
        mock_repos["politician_repo"].count = AsyncMock(return_value=200)
        mock_repos["conference_repo"].count = AsyncMock(return_value=50)

        result = await service.aggregate_activity_statistics()

        assert result["total_meetings"] == 500
        assert result["total_minutes"] == 450
        assert result["processed_minutes"] == 360
        assert result["unprocessed_minutes"] == 90
        # 360/450 * 100 = 80.0
        assert result["minutes_processing_rate"] == 80.0
        assert result["total_conversations"] == 5000
        assert result["total_politicians"] == 200
        assert result["total_conferences"] == 50

    @pytest.mark.asyncio
    async def test_aggregate_activity_statistics_zero_minutes(
        self, service, mock_repos
    ):
        """Test activity statistics aggregation with zero minutes."""
        # Setup: Has meetings but no minutes
        mock_repos["meeting_repo"].count = AsyncMock(return_value=100)
        mock_repos["minutes_repo"].count = AsyncMock(return_value=0)
        mock_repos["minutes_repo"].count_processed = AsyncMock(return_value=0)
        mock_repos["conversation_repo"].count = AsyncMock(return_value=0)
        mock_repos["politician_repo"].count = AsyncMock(return_value=50)
        mock_repos["conference_repo"].count = AsyncMock(return_value=10)

        result = await service.aggregate_activity_statistics()

        assert result["total_meetings"] == 100
        assert result["total_minutes"] == 0
        assert result["processed_minutes"] == 0
        assert result["unprocessed_minutes"] == 0
        # Edge case: should not divide by zero
        assert result["minutes_processing_rate"] == 0.0
        assert result["total_conversations"] == 0
        assert result["total_politicians"] == 50
        assert result["total_conferences"] == 10

    @pytest.mark.asyncio
    async def test_aggregate_activity_statistics_all_zero(self, service, mock_repos):
        """Test activity statistics aggregation with all zeros."""
        # Setup: No data at all
        mock_repos["meeting_repo"].count = AsyncMock(return_value=0)
        mock_repos["minutes_repo"].count = AsyncMock(return_value=0)
        mock_repos["minutes_repo"].count_processed = AsyncMock(return_value=0)
        mock_repos["conversation_repo"].count = AsyncMock(return_value=0)
        mock_repos["politician_repo"].count = AsyncMock(return_value=0)
        mock_repos["conference_repo"].count = AsyncMock(return_value=0)

        result = await service.aggregate_activity_statistics()

        assert result["total_meetings"] == 0
        assert result["total_minutes"] == 0
        assert result["processed_minutes"] == 0
        assert result["unprocessed_minutes"] == 0
        assert result["minutes_processing_rate"] == 0.0
        assert result["total_conversations"] == 0
        assert result["total_politicians"] == 0
        assert result["total_conferences"] == 0
