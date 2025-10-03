"""Tests for PoliticianStatisticsQuery."""

from unittest.mock import Mock

import pytest

from src.application.queries.politician_statistics_query import (
    PoliticianStatisticsQuery,
)


class TestPoliticianStatisticsQuery:
    """Test cases for PoliticianStatisticsQuery."""

    @pytest.mark.asyncio
    async def test_get_party_statistics_success(self):
        """Test successful retrieval of party statistics."""
        # Create mock connection
        mock_conn = Mock()
        mock_result = Mock()

        # Create mock row data
        mock_row_1 = Mock()
        mock_row_1.party_id = 1
        mock_row_1.party_name = "Party A"
        mock_row_1.extracted_total = 10
        mock_row_1.extracted_pending = 3
        mock_row_1.extracted_reviewed = 2
        mock_row_1.extracted_approved = 4
        mock_row_1.extracted_rejected = 1
        mock_row_1.extracted_converted = 0
        mock_row_1.politicians_total = 15

        mock_row_2 = Mock()
        mock_row_2.party_id = 2
        mock_row_2.party_name = "Party B"
        mock_row_2.extracted_total = 5
        mock_row_2.extracted_pending = 2
        mock_row_2.extracted_reviewed = 1
        mock_row_2.extracted_approved = 1
        mock_row_2.extracted_rejected = 0
        mock_row_2.extracted_converted = 1
        mock_row_2.politicians_total = 8

        mock_result.fetchall.return_value = [mock_row_1, mock_row_2]
        mock_conn.execute.return_value = mock_result

        # Create query instance and test
        query = PoliticianStatisticsQuery(mock_conn)
        stats = await query.get_party_statistics()

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

    @pytest.mark.asyncio
    async def test_get_party_statistics_empty_result(self):
        """Test when no parties exist."""
        # Create mock connection
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        mock_conn.execute.return_value = mock_result

        # Create query instance and test
        query = PoliticianStatisticsQuery(mock_conn)
        stats = await query.get_party_statistics()

        # Assertions
        assert stats == []

    @pytest.mark.asyncio
    async def test_get_party_statistics_by_id_success(self):
        """Test successful retrieval of single party statistics."""
        # Create mock connection
        mock_conn = Mock()
        mock_result = Mock()

        # Create mock row data
        mock_row = Mock()
        mock_row.party_id = 1
        mock_row.party_name = "Party A"
        mock_row.extracted_total = 10
        mock_row.extracted_pending = 3
        mock_row.extracted_reviewed = 2
        mock_row.extracted_approved = 4
        mock_row.extracted_rejected = 1
        mock_row.extracted_converted = 0
        mock_row.politicians_total = 15

        mock_result.fetchone.return_value = mock_row
        mock_conn.execute.return_value = mock_result

        # Create query instance and test
        query = PoliticianStatisticsQuery(mock_conn)
        stats = await query.get_party_statistics_by_id(1)

        # Assertions
        assert stats is not None
        assert stats["party_id"] == 1
        assert stats["party_name"] == "Party A"
        assert stats["extracted_total"] == 10
        assert stats["politicians_total"] == 15

    @pytest.mark.asyncio
    async def test_get_party_statistics_by_id_not_found(self):
        """Test when party ID doesn't exist."""
        # Create mock connection
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_conn.execute.return_value = mock_result

        # Create query instance and test
        query = PoliticianStatisticsQuery(mock_conn)
        stats = await query.get_party_statistics_by_id(999)

        # Assertions
        assert stats is None

    @pytest.mark.asyncio
    async def test_statistics_type_hints(self):
        """Test that returned statistics match the expected TypedDict structure."""
        # Create mock connection
        mock_conn = Mock()
        mock_result = Mock()

        # Create mock row data
        mock_row = Mock()
        mock_row.party_id = 1
        mock_row.party_name = "Party A"
        mock_row.extracted_total = 10
        mock_row.extracted_pending = 3
        mock_row.extracted_reviewed = 2
        mock_row.extracted_approved = 4
        mock_row.extracted_rejected = 1
        mock_row.extracted_converted = 0
        mock_row.politicians_total = 15

        mock_result.fetchall.return_value = [mock_row]
        mock_conn.execute.return_value = mock_result

        # Create query instance and test
        query = PoliticianStatisticsQuery(mock_conn)
        stats = await query.get_party_statistics()

        # Verify that the structure matches PartyStatistics TypedDict
        first_stat = stats[0]
        expected_keys = {
            "party_id",
            "party_name",
            "extracted_total",
            "extracted_pending",
            "extracted_reviewed",
            "extracted_approved",
            "extracted_rejected",
            "extracted_converted",
            "politicians_total",
        }
        assert set(first_stat.keys()) == expected_keys

        # Verify value types
        assert isinstance(first_stat["party_id"], int)
        assert isinstance(first_stat["party_name"], str)
        assert isinstance(first_stat["extracted_total"], int)
        assert isinstance(first_stat["politicians_total"], int)
