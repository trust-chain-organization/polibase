"""Tests for extracted conference member repository"""

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from src.database.extracted_conference_member_repository import (
    ExtractedConferenceMemberRepository,
)


class TestExtractedConferenceMemberRepository:
    """Test cases for ExtractedConferenceMemberRepository"""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection"""
        connection = Mock()
        connection.execute = Mock()
        connection.commit = Mock()
        connection.rollback = Mock()
        return connection

    @pytest.fixture
    @patch("src.database.extracted_conference_member_repository.get_db_engine")
    def repository(self, mock_get_engine, mock_connection):
        """Create a repository instance with mocked engine"""
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        repo = ExtractedConferenceMemberRepository()
        # Inject mock connection
        repo.connection = mock_connection
        return repo

    def test_create_extracted_member(self, repository):
        """Test creating an extracted member"""
        # Setup
        # Mock the execute result
        mock_result = Mock()
        mock_result.fetchone.return_value = [1]  # Return member ID
        repository.connection.execute.return_value = mock_result

        # Execute
        result = repository.create_extracted_member(
            conference_id=1,
            extracted_name="山田太郎",
            source_url="https://example.com/members",
            extracted_role="委員長",
            extracted_party_name="自民党",
            additional_info="追加情報",
        )

        # Assert
        assert result == 1
        repository.connection.commit.assert_called_once()

    def test_create_extracted_member_error(self, repository):
        """Test error handling in create_extracted_member"""
        # Setup
        repository.connection.execute.side_effect = Exception("DB Error")

        # Execute
        result = repository.create_extracted_member(
            conference_id=1,
            extracted_name="山田太郎",
            source_url="https://example.com/members",
        )

        # Assert
        assert result is None
        repository.connection.rollback.assert_called_once()

    def test_get_pending_members(self, repository):
        """Test getting pending members"""
        # Setup
        mock_result = Mock()
        mock_row1 = Mock()
        mock_row1.id = 1
        mock_row1.extracted_name = "山田太郎"
        mock_row1.extracted_role = "委員長"
        mock_row1.extracted_party_name = "自民党"

        mock_row2 = Mock()
        mock_row2.id = 2
        mock_row2.extracted_name = "田中花子"
        mock_row2.extracted_role = "副委員長"
        mock_row2.extracted_party_name = "立憲民主党"

        mock_result.fetchall.return_value = [mock_row1, mock_row2]
        repository.connection.execute.return_value = mock_result

        # Execute
        result = repository.get_pending_members(1)

        # Assert
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["extracted_name"] == "山田太郎"
        assert result[1]["id"] == 2
        assert result[1]["extracted_name"] == "田中花子"

    def test_get_pending_members_with_limit(self, repository):
        """Test getting pending members with limit"""
        # Setup
        mock_result = Mock()
        mock_result.fetchall.return_value = []
        repository.connection.execute.return_value = mock_result

        # Execute
        repository.get_pending_members(1, limit=10)

        # Assert - check SQL contains LIMIT
        call_args = repository.connection.execute.call_args
        assert "LIMIT :limit" in str(call_args[0][0])
        assert call_args[0][1]["limit"] == 10

    def test_update_matching_result(self, repository):
        """Test updating member matching status"""
        # Execute
        repository.update_matching_result(
            member_id=1,
            matched_politician_id=100,
            matching_confidence=0.85,
            matching_status="matched",
        )

        # Assert
        repository.connection.execute.assert_called_once()
        repository.connection.commit.assert_called_once()

        # Check parameters
        call_args = repository.connection.execute.call_args
        params = call_args[0][1]
        assert params["member_id"] == 1
        assert params["politician_id"] == 100
        assert params["confidence"] == 0.85
        assert params["status"] == "matched"

    def test_update_matching_result_no_match(self, repository):
        """Test updating member with no match"""
        # Execute
        repository.update_matching_result(
            member_id=1,
            matched_politician_id=None,
            matching_confidence=0.0,
            matching_status="no_match",
        )

        # Assert
        repository.connection.execute.assert_called_once()
        call_args = repository.connection.execute.call_args
        params = call_args[0][1]
        assert params["politician_id"] is None
        assert params["status"] == "no_match"

    def test_delete_extracted_members(self, repository):
        """Test deleting extracted members"""
        # Execute
        repository.delete_extracted_members(1)

        # Assert
        repository.connection.execute.assert_called_once()
        repository.connection.commit.assert_called_once()

        # Check SQL contains DELETE
        call_args = repository.connection.execute.call_args
        assert "DELETE FROM extracted_conference_members" in str(call_args[0][0])

    def test_get_matched_members(self, repository):
        """Test getting matched members"""
        # Setup
        mock_result = Mock()
        mock_row = Mock()
        mock_row.id = 1
        mock_row.extracted_name = "山田太郎"
        mock_row.extracted_role = "委員長"
        mock_row.matched_politician_id = 100
        mock_row.matching_confidence = Decimal("0.95")

        mock_result.fetchall.return_value = [mock_row]
        repository.connection.execute.return_value = mock_result

        # Execute
        result = repository.get_matched_members(1)

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["matched_politician_id"] == 100
        assert result[0]["matching_confidence"] == Decimal("0.95")
