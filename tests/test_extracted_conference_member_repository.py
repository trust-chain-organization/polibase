"""Tests for extracted conference member repository"""

from decimal import Decimal
from unittest.mock import Mock

import pytest


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
    def repository(self, mock_connection):
        """Create a repository instance with mocked connection"""
        repo = Mock()
        # Mock the connection attribute
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

        # Execute and expect SaveError to be raised
        from src.exceptions import SaveError

        with pytest.raises(SaveError) as exc_info:
            repository.create_extracted_member(
                conference_id=1,
                extracted_name="山田太郎",
                source_url="https://example.com/members",
            )

        # Assert
        assert "Unexpected error creating extracted member" in str(exc_info.value)
        repository.connection.rollback.assert_called_once()

    def test_get_pending_members(self, repository):
        """Test getting pending members"""
        # Setup
        mock_result = Mock()
        mock_row1 = Mock()
        mock_row1.id = 1
        mock_row1.conference_id = 1
        mock_row1.extracted_name = "山田太郎"
        mock_row1.extracted_role = "委員長"
        mock_row1.extracted_party_name = "自民党"
        mock_row1.source_url = "https://example.com"
        mock_row1.additional_info = None
        mock_row1.extracted_at = None
        mock_row1.conference_name = "総務委員会"
        mock_row1.governing_body_name = "国"

        mock_row2 = Mock()
        mock_row2.id = 2
        mock_row2.conference_id = 1
        mock_row2.extracted_name = "田中花子"
        mock_row2.extracted_role = "副委員長"
        mock_row2.extracted_party_name = "立憲民主党"
        mock_row2.source_url = "https://example.com"
        mock_row2.additional_info = None
        mock_row2.extracted_at = None
        mock_row2.conference_name = "総務委員会"
        mock_row2.governing_body_name = "国"

        # Mock iterator behavior instead of fetchall
        mock_result.__iter__ = Mock(return_value=iter([mock_row1, mock_row2]))
        repository.connection.execute.return_value = mock_result

        # Execute
        result = repository.get_pending_members(1)

        # Assert
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["extracted_name"] == "山田太郎"
        assert result[1]["id"] == 2
        assert result[1]["extracted_name"] == "田中花子"

    def test_get_pending_members_no_conference_filter(self, repository):
        """Test getting pending members without conference filter"""
        # Setup
        mock_result = Mock()
        mock_row = Mock()
        mock_row.id = 1
        mock_row.conference_id = 1
        mock_row.extracted_name = "山田太郎"
        mock_row.extracted_role = "委員長"
        mock_row.extracted_party_name = "自民党"
        mock_row.source_url = "https://example.com"
        mock_row.additional_info = None
        mock_row.extracted_at = None
        mock_row.conference_name = "総務委員会"
        mock_row.governing_body_name = "国"

        # Mock iterator behavior
        mock_result.__iter__ = Mock(return_value=iter([mock_row]))
        repository.connection.execute.return_value = mock_result

        # Execute - call without conference_id to test the else branch
        result = repository.get_pending_members()

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == 1
        # Check that the query was called without conference filter
        call_args = repository.connection.execute.call_args
        assert "conference_id" not in call_args[0][1]  # No conference_id in params

    def test_update_matching_result(self, repository):
        """Test updating member matching status"""
        # Execute
        result = repository.update_matching_result(
            member_id=1,
            matched_politician_id=100,
            matching_confidence=0.85,
            matching_status="matched",
        )

        # Assert
        assert result is True  # Method returns True on success
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
        result = repository.update_matching_result(
            member_id=1,
            matched_politician_id=None,
            matching_confidence=0.0,
            matching_status="no_match",
        )

        # Assert
        assert result is True  # Method returns True on success
        repository.connection.execute.assert_called_once()
        call_args = repository.connection.execute.call_args
        params = call_args[0][1]
        assert params["politician_id"] is None
        assert params["status"] == "no_match"

    def test_delete_extracted_members(self, repository):
        """Test deleting extracted members"""
        # Setup - mock rowcount
        mock_result = Mock()
        mock_result.rowcount = 3
        repository.connection.execute.return_value = mock_result

        # Execute
        deleted_count = repository.delete_extracted_members(1)

        # Assert
        assert deleted_count == 3
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
        mock_row.conference_id = 1
        mock_row.extracted_name = "山田太郎"
        mock_row.extracted_role = "委員長"
        mock_row.extracted_party_name = "自民党"
        mock_row.matched_politician_id = 100
        mock_row.matching_confidence = Decimal("0.95")
        mock_row.matching_status = "matched"
        mock_row.matched_at = None
        mock_row.politician_name = "山田太郎"
        mock_row.politician_party_name = "自民党"
        mock_row.conference_name = "総務委員会"

        # Mock iterator behavior instead of fetchall
        mock_result.__iter__ = Mock(return_value=iter([mock_row]))
        repository.connection.execute.return_value = mock_result

        # Execute
        result = repository.get_matched_members(1)

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["matched_politician_id"] == 100
        assert result[0]["matching_confidence"] == Decimal("0.95")

    def test_get_extraction_summary(self, repository):
        """Test getting extraction summary"""
        # Setup
        mock_result = Mock()
        # Return tuples instead of Mock objects with attributes
        mock_rows = [
            ("pending", 5),
            ("matched", 10),
            ("no_match", 3),
        ]

        # Mock iterator behavior
        mock_result.__iter__ = Mock(return_value=iter(mock_rows))
        repository.connection.execute.return_value = mock_result

        # Execute
        result = repository.get_extraction_summary()

        # Assert
        assert result["pending"] == 5
        assert result["matched"] == 10
        assert result["no_match"] == 3
        assert result["needs_review"] == 0  # Default value when not in results
        assert result["total"] == 18  # 5 + 10 + 3
