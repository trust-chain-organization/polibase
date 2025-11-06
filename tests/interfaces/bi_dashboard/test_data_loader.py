"""Tests for BI Dashboard data loader.

This module contains tests for data loading functions in the BI Dashboard.
"""

from unittest.mock import AsyncMock, Mock, patch

import pandas as pd

from src.interfaces.bi_dashboard.data.data_loader import (
    get_activity_trend_data,
    get_coverage_stats,
    get_governing_body_coverage_data,
    get_meeting_coverage_data,
    get_prefecture_coverage,
    get_speaker_matching_data,
    load_governing_bodies_coverage,
)


class TestLoadGoverningBodiesCoverage:
    """Tests for load_governing_bodies_coverage function."""

    @patch("src.interfaces.bi_dashboard.data.data_loader.create_engine")
    @patch("pandas.read_sql_query")
    def test_load_governing_bodies_coverage_returns_dataframe(
        self, mock_read_sql: Mock, mock_create_engine: Mock
    ) -> None:
        """Test that load_governing_bodies_coverage returns a DataFrame."""
        # Arrange
        mock_engine = Mock()
        mock_conn = Mock()
        mock_create_engine.return_value = mock_engine
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)

        mock_df = pd.DataFrame(
            {
                "id": [1, 2],
                "name": ["北海道議会", "東京都議会"],
                "organization_type": ["都道府県", "都道府県"],
                "prefecture": ["北海道", "東京都"],
                "has_data": [True, False],
            }
        )
        mock_read_sql.return_value = mock_df

        # Act
        result = load_governing_bodies_coverage()

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == [
            "id",
            "name",
            "organization_type",
            "prefecture",
            "has_data",
        ]


class TestGetCoverageStats:
    """Tests for get_coverage_stats function."""

    @patch(
        "src.interfaces.bi_dashboard.data.data_loader.load_governing_bodies_coverage"
    )
    def test_get_coverage_stats_returns_dict(self, mock_load: Mock) -> None:
        """Test that get_coverage_stats returns expected statistics."""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "id": [1, 2, 3, 4],
                "name": ["A", "B", "C", "D"],
                "organization_type": ["国", "都道府県", "都道府県", "市町村"],
                "prefecture": ["", "北海道", "東京都", "札幌市"],
                "has_data": [True, True, False, False],
            }
        )
        mock_load.return_value = mock_df

        # Act
        result = get_coverage_stats()

        # Assert
        assert isinstance(result, dict)
        assert result["total"] == 4
        assert result["covered"] == 2
        assert result["coverage_rate"] == 50.0
        assert "by_type" in result


class TestGetPrefectureCoverage:
    """Tests for get_prefecture_coverage function."""

    @patch(
        "src.interfaces.bi_dashboard.data.data_loader.load_governing_bodies_coverage"
    )
    def test_get_prefecture_coverage_returns_dataframe(self, mock_load: Mock) -> None:
        """Test that get_prefecture_coverage returns DataFrame with coverage stats."""
        # Arrange
        mock_df = pd.DataFrame(
            {
                "id": [1, 2, 3, 4],
                "name": ["A", "B", "C", "D"],
                "organization_type": ["市町村", "市町村", "市町村", "市町村"],
                "prefecture": ["北海道", "北海道", "東京都", "東京都"],
                "has_data": [True, True, False, True],
            }
        )
        mock_load.return_value = mock_df

        # Act
        result = get_prefecture_coverage()

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert "prefecture" in result.columns
        assert "total" in result.columns
        assert "covered" in result.columns
        assert "coverage_rate" in result.columns


class TestGetMeetingCoverageData:
    """Tests for get_meeting_coverage_data function."""

    @patch("src.interfaces.bi_dashboard.data.data_loader._get_usecase_dependencies")
    def test_get_meeting_coverage_data_returns_dict(self, mock_get_deps: Mock) -> None:
        """Test that get_meeting_coverage_data returns expected data."""
        # Arrange
        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_get_deps.return_value = (mock_session, mock_repo)

        mock_usecase = AsyncMock()
        mock_usecase.execute.return_value = {
            "total_meetings": 100,
            "with_minutes": 80,
            "with_conversations": 70,
            "average_conversations_per_meeting": 15.5,
            "meetings_by_conference": {"会議体A": 50, "会議体B": 50},
        }

        with patch(
            "src.interfaces.bi_dashboard.data.data_loader.ViewMeetingCoverageUseCase",
            return_value=mock_usecase,
        ):
            # Act
            result = get_meeting_coverage_data()

        # Assert
        assert isinstance(result, dict)
        assert result["total_meetings"] == 100
        assert result["with_minutes"] == 80
        assert "meetings_by_conference" in result
        mock_session.close.assert_called_once()


class TestGetSpeakerMatchingData:
    """Tests for get_speaker_matching_data function."""

    @patch("src.interfaces.bi_dashboard.data.data_loader._get_usecase_dependencies")
    def test_get_speaker_matching_data_returns_dict(self, mock_get_deps: Mock) -> None:
        """Test that get_speaker_matching_data returns expected data."""
        # Arrange
        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_get_deps.return_value = (mock_session, mock_repo)

        mock_usecase = AsyncMock()
        mock_usecase.execute.return_value = {
            "total_speakers": 100,
            "matched_speakers": 80,
            "unmatched_speakers": 20,
            "matching_rate": 80.0,
            "total_conversations": 1000,
            "linked_conversations": 900,
            "linkage_rate": 90.0,
        }

        with patch(
            "src.interfaces.bi_dashboard.data.data_loader.ViewSpeakerMatchingStatsUseCase",
            return_value=mock_usecase,
        ):
            # Act
            result = get_speaker_matching_data()

        # Assert
        assert isinstance(result, dict)
        assert result["total_speakers"] == 100
        assert result["matching_rate"] == 80.0
        assert result["linkage_rate"] == 90.0
        mock_session.close.assert_called_once()


class TestGetActivityTrendData:
    """Tests for get_activity_trend_data function."""

    @patch("src.interfaces.bi_dashboard.data.data_loader._get_usecase_dependencies")
    def test_get_activity_trend_data_returns_list(self, mock_get_deps: Mock) -> None:
        """Test that get_activity_trend_data returns expected data."""
        # Arrange
        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_get_deps.return_value = (mock_session, mock_repo)

        mock_usecase = AsyncMock()
        mock_usecase.execute.return_value = [
            {
                "date": "2025-01-01",
                "meetings_count": 10,
                "conversations_count": 100,
                "speakers_count": 50,
                "politicians_count": 30,
            },
            {
                "date": "2025-01-02",
                "meetings_count": 15,
                "conversations_count": 150,
                "speakers_count": 60,
                "politicians_count": 35,
            },
        ]

        with patch(
            "src.interfaces.bi_dashboard.data.data_loader.ViewActivityTrendUseCase",
            return_value=mock_usecase,
        ):
            # Act
            result = get_activity_trend_data("30d")

        # Assert
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["meetings_count"] == 10
        assert result[1]["meetings_count"] == 15
        mock_session.close.assert_called_once()


class TestGetGoverningBodyCoverageData:
    """Tests for get_governing_body_coverage_data function."""

    @patch("src.interfaces.bi_dashboard.data.data_loader._get_usecase_dependencies")
    def test_get_governing_body_coverage_data_returns_dict(
        self, mock_get_deps: Mock
    ) -> None:
        """Test that get_governing_body_coverage_data returns expected data."""
        # Arrange
        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_get_deps.return_value = (mock_session, mock_repo)

        mock_usecase = AsyncMock()
        mock_usecase.execute.return_value = {
            "total": 1966,
            "with_conferences": 100,
            "with_meetings": 50,
            "coverage_percentage": 5.0,
        }

        with patch(
            "src.interfaces.bi_dashboard.data.data_loader.ViewGoverningBodyCoverageUseCase",
            return_value=mock_usecase,
        ):
            # Act
            result = get_governing_body_coverage_data()

        # Assert
        assert isinstance(result, dict)
        assert result["total"] == 1966
        assert result["coverage_percentage"] == 5.0
        mock_session.close.assert_called_once()
