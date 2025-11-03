"""Tests for data coverage view use cases."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.application.usecases.view_data_coverage_usecase import (
    ViewActivityTrendUseCase,
    ViewGoverningBodyCoverageUseCase,
    ViewMeetingCoverageUseCase,
    ViewSpeakerMatchingStatsUseCase,
)


@pytest.mark.asyncio
class TestViewGoverningBodyCoverageUseCase:
    """Test cases for ViewGoverningBodyCoverageUseCase."""

    async def test_execute_success(self):
        """Test successful retrieval of governing body coverage statistics."""
        # Create mock repository
        mock_repo = Mock()

        # Setup mock return
        mock_repo.get_governing_body_stats = AsyncMock(
            return_value={
                "total": 1966,
                "with_conferences": 500,
                "with_meetings": 300,
                "coverage_percentage": 25.43,
            }
        )

        # Create use case and test
        use_case = ViewGoverningBodyCoverageUseCase(mock_repo)
        result = await use_case.execute()

        # Assertions
        assert result["total"] == 1966
        assert result["with_conferences"] == 500
        assert result["with_meetings"] == 300
        assert result["coverage_percentage"] == 25.43

        # Verify repository was called
        mock_repo.get_governing_body_stats.assert_called_once()

    async def test_execute_handles_exception(self):
        """Test that execute properly raises exceptions from repository."""
        # Create mock repository that raises an exception
        mock_repo = Mock()
        mock_repo.get_governing_body_stats = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Create use case
        use_case = ViewGoverningBodyCoverageUseCase(mock_repo)

        # Verify exception is raised
        with pytest.raises(Exception, match="Database error"):
            await use_case.execute()


@pytest.mark.asyncio
class TestViewMeetingCoverageUseCase:
    """Test cases for ViewMeetingCoverageUseCase."""

    async def test_execute_success(self):
        """Test successful retrieval of meeting coverage statistics."""
        # Create mock repository
        mock_repo = Mock()

        # Setup mock return
        mock_repo.get_meeting_stats = AsyncMock(
            return_value={
                "total_meetings": 1000,
                "with_minutes": 800,
                "with_conversations": 600,
                "average_conversations_per_meeting": 15.5,
                "meetings_by_conference": {
                    "Conference A": 300,
                    "Conference B": 400,
                    "Conference C": 300,
                },
            }
        )

        # Create use case and test
        use_case = ViewMeetingCoverageUseCase(mock_repo)
        result = await use_case.execute()

        # Assertions
        assert result["total_meetings"] == 1000
        assert result["with_minutes"] == 800
        assert result["with_conversations"] == 600
        assert result["average_conversations_per_meeting"] == 15.5
        assert len(result["meetings_by_conference"]) == 3
        assert result["meetings_by_conference"]["Conference A"] == 300

        # Verify repository was called
        mock_repo.get_meeting_stats.assert_called_once()

    async def test_execute_handles_exception(self):
        """Test that execute properly raises exceptions from repository."""
        # Create mock repository that raises an exception
        mock_repo = Mock()
        mock_repo.get_meeting_stats = AsyncMock(side_effect=Exception("Database error"))

        # Create use case
        use_case = ViewMeetingCoverageUseCase(mock_repo)

        # Verify exception is raised
        with pytest.raises(Exception, match="Database error"):
            await use_case.execute()


@pytest.mark.asyncio
class TestViewSpeakerMatchingStatsUseCase:
    """Test cases for ViewSpeakerMatchingStatsUseCase."""

    async def test_execute_success(self):
        """Test successful retrieval of speaker matching statistics."""
        # Create mock repository
        mock_repo = Mock()

        # Setup mock return
        mock_repo.get_speaker_matching_stats = AsyncMock(
            return_value={
                "total_speakers": 5000,
                "matched_speakers": 3500,
                "unmatched_speakers": 1500,
                "matching_rate": 70.0,
                "total_conversations": 10000,
                "linked_conversations": 8000,
                "linkage_rate": 80.0,
            }
        )

        # Create use case and test
        use_case = ViewSpeakerMatchingStatsUseCase(mock_repo)
        result = await use_case.execute()

        # Assertions
        assert result["total_speakers"] == 5000
        assert result["matched_speakers"] == 3500
        assert result["unmatched_speakers"] == 1500
        assert result["matching_rate"] == 70.0
        assert result["total_conversations"] == 10000
        assert result["linked_conversations"] == 8000
        assert result["linkage_rate"] == 80.0

        # Verify repository was called
        mock_repo.get_speaker_matching_stats.assert_called_once()

    async def test_execute_with_zero_values(self):
        """Test execution when there are no speakers or conversations."""
        # Create mock repository
        mock_repo = Mock()

        # Setup mock return with zeros
        mock_repo.get_speaker_matching_stats = AsyncMock(
            return_value={
                "total_speakers": 0,
                "matched_speakers": 0,
                "unmatched_speakers": 0,
                "matching_rate": 0.0,
                "total_conversations": 0,
                "linked_conversations": 0,
                "linkage_rate": 0.0,
            }
        )

        # Create use case and test
        use_case = ViewSpeakerMatchingStatsUseCase(mock_repo)
        result = await use_case.execute()

        # Assertions
        assert result["total_speakers"] == 0
        assert result["matching_rate"] == 0.0

    async def test_execute_handles_exception(self):
        """Test that execute properly raises exceptions from repository."""
        # Create mock repository that raises an exception
        mock_repo = Mock()
        mock_repo.get_speaker_matching_stats = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Create use case
        use_case = ViewSpeakerMatchingStatsUseCase(mock_repo)

        # Verify exception is raised
        with pytest.raises(Exception, match="Database error"):
            await use_case.execute()


@pytest.mark.asyncio
class TestViewActivityTrendUseCase:
    """Test cases for ViewActivityTrendUseCase."""

    async def test_execute_success_with_30d_period(self):
        """Test successful retrieval of activity trend data for 30 days."""
        # Create mock repository
        mock_repo = Mock()

        # Setup mock return
        mock_trend_data = [
            {
                "date": "2025-01-01",
                "meetings_count": 5,
                "conversations_count": 50,
                "speakers_count": 10,
                "politicians_count": 3,
            },
            {
                "date": "2025-01-02",
                "meetings_count": 3,
                "conversations_count": 30,
                "speakers_count": 8,
                "politicians_count": 2,
            },
            {
                "date": "2025-01-03",
                "meetings_count": 7,
                "conversations_count": 70,
                "speakers_count": 15,
                "politicians_count": 5,
            },
        ]
        mock_repo.get_activity_trend = AsyncMock(return_value=mock_trend_data)

        # Create use case and test
        use_case = ViewActivityTrendUseCase(mock_repo)
        result = await use_case.execute({"period": "30d"})

        # Assertions
        assert len(result) == 3
        assert result[0]["date"] == "2025-01-01"
        assert result[0]["meetings_count"] == 5
        assert result[0]["conversations_count"] == 50
        assert result[1]["date"] == "2025-01-02"
        assert result[2]["date"] == "2025-01-03"

        # Verify repository was called with correct period
        mock_repo.get_activity_trend.assert_called_once_with("30d")

    async def test_execute_success_with_7d_period(self):
        """Test successful retrieval of activity trend data for 7 days."""
        # Create mock repository
        mock_repo = Mock()

        # Setup mock return
        mock_trend_data = [
            {
                "date": "2025-01-01",
                "meetings_count": 5,
                "conversations_count": 50,
                "speakers_count": 10,
                "politicians_count": 3,
            }
        ]
        mock_repo.get_activity_trend = AsyncMock(return_value=mock_trend_data)

        # Create use case and test
        use_case = ViewActivityTrendUseCase(mock_repo)
        result = await use_case.execute({"period": "7d"})

        # Assertions
        assert len(result) == 1

        # Verify repository was called with correct period
        mock_repo.get_activity_trend.assert_called_once_with("7d")

    async def test_execute_with_empty_result(self):
        """Test execution when there's no activity data."""
        # Create mock repository
        mock_repo = Mock()

        # Setup mock return with empty list
        mock_repo.get_activity_trend = AsyncMock(return_value=[])

        # Create use case and test
        use_case = ViewActivityTrendUseCase(mock_repo)
        result = await use_case.execute({"period": "30d"})

        # Assertions
        assert result == []

    async def test_execute_handles_exception(self):
        """Test that execute properly raises exceptions from repository."""
        # Create mock repository that raises an exception
        mock_repo = Mock()
        mock_repo.get_activity_trend = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Create use case
        use_case = ViewActivityTrendUseCase(mock_repo)

        # Verify exception is raised
        with pytest.raises(Exception, match="Database error"):
            await use_case.execute({"period": "30d"})
