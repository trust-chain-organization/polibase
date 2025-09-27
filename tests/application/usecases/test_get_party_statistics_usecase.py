"""Tests for GetPartyStatisticsUseCase."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.application.usecases.get_party_statistics_usecase import (
    GetPartyStatisticsUseCase,
)
from src.domain.entities.political_party import PoliticalParty


@pytest.mark.asyncio
class TestGetPartyStatisticsUseCase:
    """Test cases for GetPartyStatisticsUseCase."""

    async def test_execute_success(self):
        """Test successful retrieval of party statistics."""
        # Create mock repositories
        mock_party_repo = Mock()
        mock_extracted_repo = Mock()
        mock_politician_repo = Mock()

        # Create mock parties
        party1 = Mock(spec=PoliticalParty)
        party1.id = 1
        party1.name = "Party A"

        party2 = Mock(spec=PoliticalParty)
        party2.id = 2
        party2.name = "Party B"

        # Setup mock returns
        mock_party_repo.get_all = AsyncMock(return_value=[party1, party2])

        mock_extracted_repo.get_statistics_by_party = AsyncMock(
            side_effect=[
                {
                    "total": 10,
                    "pending": 3,
                    "reviewed": 2,
                    "approved": 4,
                    "rejected": 1,
                    "converted": 0,
                },
                {
                    "total": 5,
                    "pending": 2,
                    "reviewed": 1,
                    "approved": 1,
                    "rejected": 0,
                    "converted": 1,
                },
            ]
        )

        mock_politician_repo.count_by_party = AsyncMock(side_effect=[15, 8])

        # Create use case and test
        use_case = GetPartyStatisticsUseCase(
            mock_party_repo, mock_extracted_repo, mock_politician_repo
        )
        stats = await use_case.execute()

        # Assertions
        assert len(stats) == 2

        # Check first party statistics
        assert stats[0]["party_id"] == 1
        assert stats[0]["party_name"] == "Party A"
        assert stats[0]["extracted_total"] == 10
        assert stats[0]["extracted_pending"] == 3
        assert stats[0]["extracted_reviewed"] == 2
        assert stats[0]["extracted_approved"] == 4
        assert stats[0]["extracted_rejected"] == 1
        assert stats[0]["extracted_converted"] == 0
        assert stats[0]["politicians_total"] == 15

        # Check second party statistics
        assert stats[1]["party_id"] == 2
        assert stats[1]["party_name"] == "Party B"
        assert stats[1]["extracted_total"] == 5
        assert stats[1]["politicians_total"] == 8

    async def test_execute_empty_result(self):
        """Test when no parties exist."""
        # Create mock repositories
        mock_party_repo = Mock()
        mock_extracted_repo = Mock()
        mock_politician_repo = Mock()

        # Setup mock returns
        mock_party_repo.get_all = AsyncMock(return_value=[])

        # Create use case and test
        use_case = GetPartyStatisticsUseCase(
            mock_party_repo, mock_extracted_repo, mock_politician_repo
        )
        stats = await use_case.execute()

        # Assertions
        assert stats == []

    async def test_execute_by_id_success(self):
        """Test successful retrieval of single party statistics."""
        # Create mock repositories
        mock_party_repo = Mock()
        mock_extracted_repo = Mock()
        mock_politician_repo = Mock()

        # Create mock party
        party = Mock(spec=PoliticalParty)
        party.id = 1
        party.name = "Party A"

        # Setup mock returns
        mock_party_repo.get_by_id = AsyncMock(return_value=party)

        mock_extracted_repo.get_statistics_by_party = AsyncMock(
            return_value={
                "total": 10,
                "pending": 3,
                "reviewed": 2,
                "approved": 4,
                "rejected": 1,
                "converted": 0,
            }
        )

        mock_politician_repo.count_by_party = AsyncMock(return_value=15)

        # Create use case and test
        use_case = GetPartyStatisticsUseCase(
            mock_party_repo, mock_extracted_repo, mock_politician_repo
        )
        stats = await use_case.execute_by_id(1)

        # Assertions
        assert stats is not None
        assert stats["party_id"] == 1
        assert stats["party_name"] == "Party A"
        assert stats["extracted_total"] == 10
        assert stats["politicians_total"] == 15

    async def test_execute_by_id_not_found(self):
        """Test when party ID doesn't exist."""
        # Create mock repositories
        mock_party_repo = Mock()
        mock_extracted_repo = Mock()
        mock_politician_repo = Mock()

        # Setup mock returns
        mock_party_repo.get_by_id = AsyncMock(return_value=None)

        # Create use case and test
        use_case = GetPartyStatisticsUseCase(
            mock_party_repo, mock_extracted_repo, mock_politician_repo
        )
        stats = await use_case.execute_by_id(999)

        # Assertions
        assert stats is None

    async def test_statistics_sorting(self):
        """Test that statistics are sorted by party name."""
        # Create mock repositories
        mock_party_repo = Mock()
        mock_extracted_repo = Mock()
        mock_politician_repo = Mock()

        # Create mock parties (unsorted)
        party1 = Mock(spec=PoliticalParty)
        party1.id = 1
        party1.name = "Zebra Party"

        party2 = Mock(spec=PoliticalParty)
        party2.id = 2
        party2.name = "Alpha Party"

        party3 = Mock(spec=PoliticalParty)
        party3.id = 3
        party3.name = "Beta Party"

        # Setup mock returns
        mock_party_repo.get_all = AsyncMock(return_value=[party1, party2, party3])

        mock_extracted_repo.get_statistics_by_party = AsyncMock(
            return_value={
                "total": 0,
                "pending": 0,
                "reviewed": 0,
                "approved": 0,
                "rejected": 0,
                "converted": 0,
            }
        )

        mock_politician_repo.count_by_party = AsyncMock(return_value=0)

        # Create use case and test
        use_case = GetPartyStatisticsUseCase(
            mock_party_repo, mock_extracted_repo, mock_politician_repo
        )
        stats = await use_case.execute()

        # Verify sorting
        assert len(stats) == 3
        assert stats[0]["party_name"] == "Alpha Party"
        assert stats[1]["party_name"] == "Beta Party"
        assert stats[2]["party_name"] == "Zebra Party"
