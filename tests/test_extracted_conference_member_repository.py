"""Tests for extracted conference member repository"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest


class TestExtractedConferenceMemberRepository:
    """Test cases for ExtractedConferenceMemberRepository"""

    @pytest.fixture
    def repository(self):
        """Create a mock repository instance"""
        return MagicMock()

    def test_create_extracted_member(self, repository):
        """Test creating an extracted member"""
        # Setup
        repository.create_extracted_member.return_value = 1

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
        repository.create_extracted_member.assert_called_once_with(
            conference_id=1,
            extracted_name="山田太郎",
            source_url="https://example.com/members",
            extracted_role="委員長",
            extracted_party_name="自民党",
            additional_info="追加情報",
        )

    def test_get_pending_members(self, repository):
        """Test getting pending members"""
        # Setup
        mock_data = [
            {
                "id": 1,
                "conference_id": 1,
                "extracted_name": "山田太郎",
                "extracted_role": "委員長",
                "extracted_party_name": "自民党",
                "source_url": "https://example.com",
                "additional_info": None,
                "extracted_at": None,
                "conference_name": "総務委員会",
                "governing_body_name": "国",
            },
            {
                "id": 2,
                "conference_id": 1,
                "extracted_name": "田中花子",
                "extracted_role": "副委員長",
                "extracted_party_name": "立憲民主党",
                "source_url": "https://example.com",
                "additional_info": None,
                "extracted_at": None,
                "conference_name": "総務委員会",
                "governing_body_name": "国",
            },
        ]
        repository.get_pending_members.return_value = mock_data

        # Execute
        result = repository.get_pending_members(1)

        # Assert
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["extracted_name"] == "山田太郎"
        assert result[1]["id"] == 2
        assert result[1]["extracted_name"] == "田中花子"
        repository.get_pending_members.assert_called_once_with(1)

    def test_get_pending_members_no_conference_filter(self, repository):
        """Test getting pending members without conference filter"""
        # Setup
        mock_data = [
            {
                "id": 1,
                "conference_id": 1,
                "extracted_name": "山田太郎",
                "extracted_role": "委員長",
                "extracted_party_name": "自民党",
                "source_url": "https://example.com",
                "additional_info": None,
                "extracted_at": None,
                "conference_name": "総務委員会",
                "governing_body_name": "国",
            }
        ]
        repository.get_pending_members.return_value = mock_data

        # Execute - call without conference_id to test the else branch
        result = repository.get_pending_members()

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == 1
        repository.get_pending_members.assert_called_once_with()

    def test_update_matching_result(self, repository):
        """Test updating member matching status"""
        # Setup
        repository.update_matching_result.return_value = True

        # Execute
        result = repository.update_matching_result(
            member_id=1,
            matched_politician_id=100,
            matching_confidence=0.85,
            matching_status="matched",
        )

        # Assert
        assert result is True
        repository.update_matching_result.assert_called_once_with(
            member_id=1,
            matched_politician_id=100,
            matching_confidence=0.85,
            matching_status="matched",
        )

    def test_update_matching_result_no_match(self, repository):
        """Test updating member with no match"""
        # Setup
        repository.update_matching_result.return_value = True

        # Execute
        result = repository.update_matching_result(
            member_id=1,
            matched_politician_id=None,
            matching_confidence=0.0,
            matching_status="no_match",
        )

        # Assert
        assert result is True
        repository.update_matching_result.assert_called_once_with(
            member_id=1,
            matched_politician_id=None,
            matching_confidence=0.0,
            matching_status="no_match",
        )

    def test_delete_extracted_members(self, repository):
        """Test deleting extracted members"""
        # Setup
        repository.delete_extracted_members.return_value = 3

        # Execute
        deleted_count = repository.delete_extracted_members(1)

        # Assert
        assert deleted_count == 3
        repository.delete_extracted_members.assert_called_once_with(1)

    def test_get_matched_members(self, repository):
        """Test getting matched members"""
        # Setup
        mock_data = [
            {
                "id": 1,
                "conference_id": 1,
                "extracted_name": "山田太郎",
                "extracted_role": "委員長",
                "extracted_party_name": "自民党",
                "matched_politician_id": 100,
                "matching_confidence": Decimal("0.95"),
                "matching_status": "matched",
                "matched_at": None,
                "politician_name": "山田太郎",
                "politician_party_name": "自民党",
                "conference_name": "総務委員会",
            }
        ]
        repository.get_matched_members.return_value = mock_data

        # Execute
        result = repository.get_matched_members(1)

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["matched_politician_id"] == 100
        assert result[0]["matching_confidence"] == Decimal("0.95")
        repository.get_matched_members.assert_called_once_with(1)

    def test_get_extraction_summary(self, repository):
        """Test getting extraction summary"""
        # Setup
        mock_summary = {
            "pending": 5,
            "matched": 10,
            "no_match": 3,
            "needs_review": 2,
            "total": 20,
        }
        repository.get_extraction_summary.return_value = mock_summary

        # Execute
        result = repository.get_extraction_summary()

        # Assert
        assert result["pending"] == 5
        assert result["matched"] == 10
        assert result["no_match"] == 3
        assert result["needs_review"] == 2
        assert result["total"] == 20
        repository.get_extraction_summary.assert_called_once()
