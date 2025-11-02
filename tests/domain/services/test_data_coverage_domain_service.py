"""Tests for data coverage domain service."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.domain.services.data_coverage_domain_service import DataCoverageDomainService


class TestDataCoverageDomainService:
    """Test cases for DataCoverageDomainService."""

    @pytest.fixture
    def governing_body_repo(self):
        """Create mock governing body repository."""
        repo = Mock()
        repo.count = AsyncMock()
        repo.count_with_conferences = AsyncMock()
        repo.count_with_meetings = AsyncMock()
        return repo

    @pytest.fixture
    def conference_repo(self):
        """Create mock conference repository."""
        repo = Mock()
        repo.count = AsyncMock()
        return repo

    @pytest.fixture
    def meeting_repo(self):
        """Create mock meeting repository."""
        repo = Mock()
        repo.count = AsyncMock()
        return repo

    @pytest.fixture
    def minutes_repo(self):
        """Create mock minutes repository."""
        repo = Mock()
        repo.count = AsyncMock()
        repo.count_processed = AsyncMock()
        return repo

    @pytest.fixture
    def speaker_repo(self):
        """Create mock speaker repository."""
        repo = Mock()
        repo.get_speaker_politician_stats = AsyncMock()
        return repo

    @pytest.fixture
    def politician_repo(self):
        """Create mock politician repository."""
        repo = Mock()
        repo.count = AsyncMock()
        return repo

    @pytest.fixture
    def conversation_repo(self):
        """Create mock conversation repository."""
        repo = Mock()
        repo.count = AsyncMock()
        return repo

    @pytest.fixture
    def service(
        self,
        governing_body_repo,
        conference_repo,
        meeting_repo,
        minutes_repo,
        speaker_repo,
        politician_repo,
        conversation_repo,
    ):
        """Create service instance with mock repositories."""
        return DataCoverageDomainService(
            governing_body_repo=governing_body_repo,
            conference_repo=conference_repo,
            meeting_repo=meeting_repo,
            minutes_repo=minutes_repo,
            speaker_repo=speaker_repo,
            politician_repo=politician_repo,
            conversation_repo=conversation_repo,
        )

    @pytest.mark.asyncio
    async def test_calculate_governing_body_coverage_with_data(
        self, service, governing_body_repo
    ):
        """Test governing body coverage calculation with data."""
        # Setup mock
        governing_body_repo.count.return_value = 300

        # Execute
        result = await service.calculate_governing_body_coverage()

        # Assert
        assert result["total"] == 1966  # Total municipalities in Japan
        assert result["registered"] == 300
        assert result["coverage_rate"] == 15.26  # 300/1966 * 100, rounded

    @pytest.mark.asyncio
    async def test_calculate_governing_body_coverage_zero_registered(
        self, service, governing_body_repo
    ):
        """Test governing body coverage calculation with no registered bodies."""
        # Setup mock
        governing_body_repo.count.return_value = 0

        # Execute
        result = await service.calculate_governing_body_coverage()

        # Assert
        assert result["total"] == 1966
        assert result["registered"] == 0
        assert result["coverage_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_calculate_meeting_coverage(self, service, governing_body_repo):
        """Test meeting coverage calculation."""
        # Setup mocks
        governing_body_repo.count.return_value = 500
        governing_body_repo.count_with_conferences.return_value = 400
        governing_body_repo.count_with_meetings.return_value = 350

        # Execute
        result = await service.calculate_meeting_coverage()

        # Assert
        assert result["total_governing_bodies"] == 500
        assert result["bodies_with_conferences"] == 400
        assert result["bodies_with_meetings"] == 350
        assert result["conference_coverage_rate"] == 80.0  # 400/500 * 100
        assert result["meeting_coverage_rate"] == 70.0  # 350/500 * 100

    @pytest.mark.asyncio
    async def test_calculate_meeting_coverage_zero_total(
        self, service, governing_body_repo
    ):
        """Test meeting coverage calculation with no governing bodies."""
        # Setup mocks
        governing_body_repo.count.return_value = 0
        governing_body_repo.count_with_conferences.return_value = 0
        governing_body_repo.count_with_meetings.return_value = 0

        # Execute
        result = await service.calculate_meeting_coverage()

        # Assert
        assert result["total_governing_bodies"] == 0
        assert result["conference_coverage_rate"] == 0.0
        assert result["meeting_coverage_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_calculate_speaker_matching_rate(self, service, speaker_repo):
        """Test speaker matching rate calculation."""
        # Setup mock
        speaker_repo.get_speaker_politician_stats.return_value = {
            "total_speakers": 1000,
            "linked_speakers": 750,
            "politician_speakers": 600,
            "linked_politician_speakers": 540,
        }

        # Execute
        result = await service.calculate_speaker_matching_rate()

        # Assert
        assert result["total_speakers"] == 1000
        assert result["linked_speakers"] == 750
        assert result["unlinked_speakers"] == 250
        assert result["overall_matching_rate"] == 75.0
        assert result["politician_speakers"] == 600
        assert result["linked_politician_speakers"] == 540
        assert result["unlinked_politician_speakers"] == 60
        assert result["politician_matching_rate"] == 90.0

    @pytest.mark.asyncio
    async def test_calculate_speaker_matching_rate_zero_speakers(
        self, service, speaker_repo
    ):
        """Test speaker matching rate calculation with no speakers."""
        # Setup mock
        speaker_repo.get_speaker_politician_stats.return_value = {
            "total_speakers": 0,
            "linked_speakers": 0,
            "politician_speakers": 0,
            "linked_politician_speakers": 0,
        }

        # Execute
        result = await service.calculate_speaker_matching_rate()

        # Assert
        assert result["total_speakers"] == 0
        assert result["overall_matching_rate"] == 0.0
        assert result["politician_matching_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_aggregate_activity_statistics(
        self,
        service,
        meeting_repo,
        minutes_repo,
        conversation_repo,
        politician_repo,
        conference_repo,
    ):
        """Test activity statistics aggregation."""
        # Setup mocks
        meeting_repo.count.return_value = 500
        minutes_repo.count.return_value = 450
        minutes_repo.count_processed.return_value = 400
        conversation_repo.count.return_value = 10000
        politician_repo.count.return_value = 1500
        conference_repo.count.return_value = 300

        # Execute
        result = await service.aggregate_activity_statistics()

        # Assert
        assert result["total_meetings"] == 500
        assert result["total_minutes"] == 450
        assert result["processed_minutes"] == 400
        assert result["unprocessed_minutes"] == 50
        assert result["minutes_processing_rate"] == 88.89  # 400/450 * 100, rounded
        assert result["total_conversations"] == 10000
        assert result["total_politicians"] == 1500
        assert result["total_conferences"] == 300

    @pytest.mark.asyncio
    async def test_aggregate_activity_statistics_zero_minutes(
        self,
        service,
        meeting_repo,
        minutes_repo,
        conversation_repo,
        politician_repo,
        conference_repo,
    ):
        """Test activity statistics aggregation with no minutes."""
        # Setup mocks
        meeting_repo.count.return_value = 100
        minutes_repo.count.return_value = 0
        minutes_repo.count_processed.return_value = 0
        conversation_repo.count.return_value = 0
        politician_repo.count.return_value = 500
        conference_repo.count.return_value = 50

        # Execute
        result = await service.aggregate_activity_statistics()

        # Assert
        assert result["total_minutes"] == 0
        assert result["minutes_processing_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_calculate_governing_body_coverage_exact_percentage(
        self, service, governing_body_repo
    ):
        """Test that coverage percentage is calculated correctly with rounding."""
        # Setup mock: 299 out of 1966 = 15.20854...%
        governing_body_repo.count.return_value = 299

        # Execute
        result = await service.calculate_governing_body_coverage()

        # Assert
        assert result["coverage_rate"] == 15.21  # Should be rounded to 2 decimals

    @pytest.mark.asyncio
    async def test_all_percentages_are_rounded_to_two_decimals(
        self,
        service,
        governing_body_repo,
        speaker_repo,
        minutes_repo,
        meeting_repo,
        conversation_repo,
        politician_repo,
        conference_repo,
    ):
        """Test that all percentage values are rounded to 2 decimal places."""
        # Setup mocks with values that produce many decimal places
        governing_body_repo.count.return_value = 333
        governing_body_repo.count_with_conferences.return_value = 222
        governing_body_repo.count_with_meetings.return_value = 111

        speaker_repo.get_speaker_politician_stats.return_value = {
            "total_speakers": 999,
            "linked_speakers": 666,
            "politician_speakers": 333,
            "linked_politician_speakers": 222,
        }

        meeting_repo.count.return_value = 100
        minutes_repo.count.return_value = 999
        minutes_repo.count_processed.return_value = 666
        conversation_repo.count.return_value = 1000
        politician_repo.count.return_value = 100
        conference_repo.count.return_value = 50

        # Execute all methods
        gov_body_result = await service.calculate_governing_body_coverage()
        meeting_result = await service.calculate_meeting_coverage()
        speaker_result = await service.calculate_speaker_matching_rate()
        activity_result = await service.aggregate_activity_statistics()

        # Assert all percentages have at most 2 decimal places
        def has_max_two_decimals(value: float) -> bool:
            return len(str(value).split(".")[-1]) <= 2 if "." in str(value) else True

        assert has_max_two_decimals(gov_body_result["coverage_rate"])
        assert has_max_two_decimals(meeting_result["conference_coverage_rate"])
        assert has_max_two_decimals(meeting_result["meeting_coverage_rate"])
        assert has_max_two_decimals(speaker_result["overall_matching_rate"])
        assert has_max_two_decimals(speaker_result["politician_matching_rate"])
        assert has_max_two_decimals(activity_result["minutes_processing_rate"])
