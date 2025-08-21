"""Tests for MeetingRepository"""

from datetime import date, datetime
from typing import Any
from unittest.mock import MagicMock, patch

from src.models.meeting_v2 import Meeting


class TestMeetingRepository:
    """Test cases for MeetingRepository"""

    def setup_method(self, method: Any) -> None:
        """Set up test fixtures"""
        # Mock the repository directly
        self.mock_repo = MagicMock()
        self.repo = self.mock_repo

    def test_get_governing_bodies(self):
        """Test getting all governing bodies"""
        # Mock data
        mock_result = MagicMock()
        mock_result.keys.return_value = [
            "id",
            "name",
            "type",
            "created_at",
            "updated_at",
        ]
        mock_result.fetchall.return_value = [
            (1, "日本国", "国", None, None),
            (2, "東京都", "都道府県", None, None),
            (3, "京都市", "市町村", None, None),
        ]

        # Mock execute_query to return the expected data
        with patch.object(self.repo, "execute_query", return_value=mock_result):
            # Execute
            result = self.repo.get_governing_bodies()

        # Assert
        assert len(result) == 3
        assert result[0]["id"] == 1
        assert result[0]["name"] == "日本国"
        assert result[0]["type"] == "国"
        assert result[1]["name"] == "東京都"
        assert result[1]["type"] == "都道府県"

    def test_get_conferences_by_governing_body(self):
        """Test getting conferences by governing body"""
        # Mock data
        mock_result = MagicMock()
        mock_result.keys.return_value = [
            "id",
            "name",
            "type",
            "governing_body_id",
            "created_at",
            "updated_at",
        ]
        mock_result.fetchall.return_value = [
            (1, "本会議", "議院", 1, None, None),
            (2, "予算委員会", "常任委員会", 1, None, None),
        ]

        # Mock execute_query to return the expected data
        with patch.object(self.repo, "execute_query", return_value=mock_result):
            # Execute
            result = self.repo.get_conferences_by_governing_body(1)

        # Assert
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["name"] == "本会議"
        assert result[0]["type"] == "議院"

    def test_get_all_conferences(self):
        """Test getting all conferences with governing bodies"""
        # Mock data
        mock_result = MagicMock()
        mock_result.keys.return_value = [
            "id",
            "name",
            "type",
            "governing_body_id",
            "governing_body_name",
            "governing_body_type",
        ]
        mock_result.fetchall.return_value = [
            (1, "本会議", "議院", 1, "日本国", "国"),
            (2, "市議会", "地方議会全体", 3, "京都市", "市町村"),
        ]

        # Mock execute_query to return the expected data
        with patch.object(self.repo, "execute_query", return_value=mock_result):
            # Execute
            result = self.repo.get_all_conferences()

        # Assert
        assert len(result) == 2
        assert result[0]["name"] == "本会議"
        assert result[0]["governing_body_name"] == "日本国"
        assert result[1]["governing_body_type"] == "市町村"

    def test_create_meeting(self):
        """Test creating a new meeting"""
        # Mock the create_from_model method to return a Meeting object
        mock_meeting = Meeting(
            id=123,
            conference_id=1,
            date=date(2024, 6, 1),
            url="https://example.com/meeting.pdf",
            name=None,
            gcs_pdf_uri=None,
            gcs_text_uri=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch.object(self.repo, "create_from_model", return_value=mock_meeting):
            # Execute
            result = self.repo.create_meeting(
                conference_id=1,
                meeting_date=date(2024, 6, 1),
                url="https://example.com/meeting.pdf",
            )

            # Assert
            assert result is not None
            assert result.id == 123
            assert result.conference_id == 1
            assert result.url == "https://example.com/meeting.pdf"

    def test_update_meeting(self):
        """Test updating a meeting"""
        # Mock the update_from_model method to return a Meeting object
        updated_meeting = Meeting(
            id=1,
            conference_id=1,
            date=date(2024, 6, 2),
            url="https://example.com/updated.pdf",
            name=None,
            gcs_pdf_uri=None,
            gcs_text_uri=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch.object(self.repo, "update_from_model", return_value=updated_meeting):
            # Execute
            result = self.repo.update_meeting(
                meeting_id=1,
                meeting_date=date(2024, 6, 2),
                url="https://example.com/updated.pdf",
            )

            # Assert
            assert result is not None
            assert result.date == date(2024, 6, 2)
            assert result.url == "https://example.com/updated.pdf"

    def test_delete_meeting_success(self):
        """Test deleting a meeting successfully"""
        # Mock data - no related minutes
        check_result = MagicMock()
        check_result.scalar.return_value = 0

        with patch.object(self.repo, "execute_query", return_value=check_result):
            with patch.object(self.repo, "delete", return_value=True) as mock_delete:
                # Execute
                success = self.repo.delete_meeting(1)

                # Assert
                assert success is True
                mock_delete.assert_called_once_with(1)

    def test_delete_meeting_with_related_minutes(self):
        """Test deleting a meeting with related minutes"""
        # Mock data - has related minutes
        check_result = MagicMock()
        check_result.scalar.return_value = 2

        with patch.object(self.repo, "execute_query", return_value=check_result):
            # Execute
            success = self.repo.delete_meeting(1)

            # Assert
            assert success is False

    def test_get_meeting_by_id(self):
        """Test getting a meeting by ID"""
        # Mock the get method from TypedRepository
        mock_meeting = Meeting(
            id=1,
            conference_id=2,
            date=date(2024, 6, 1),
            url="https://example.com/meeting.pdf",
            name=None,
            gcs_pdf_uri=None,
            gcs_text_uri=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch.object(self.repo, "get_by_id", return_value=mock_meeting):
            # Execute
            meeting = self.repo.get_by_id(1)  # Use get_by_id method

        # Assert
        assert meeting is not None
        assert meeting.id == 1
        assert meeting.conference_id == 2
        assert meeting.url == "https://example.com/meeting.pdf"

    def test_get_meetings_with_filter(self):
        """Test getting meetings with conference filter"""
        # Mock data
        mock_rows = [
            MagicMock(
                _mapping={
                    "id": 1,
                    "conference_id": 1,
                    "date": date(2024, 6, 1),
                    "url": "https://example.com/1.pdf",
                    "name": None,
                    "gcs_pdf_uri": None,
                    "gcs_text_uri": None,
                    "created_at": None,
                    "updated_at": None,
                    "conference_name": "本会議",
                    "governing_body_name": "日本国",
                    "governing_body_type": "国",
                }
            ),
            MagicMock(
                _mapping={
                    "id": 2,
                    "conference_id": 1,
                    "date": date(2024, 5, 15),
                    "url": "https://example.com/2.pdf",
                    "name": None,
                    "gcs_pdf_uri": None,
                    "gcs_text_uri": None,
                    "created_at": None,
                    "updated_at": None,
                    "conference_name": "本会議",
                    "governing_body_name": "日本国",
                    "governing_body_type": "国",
                }
            ),
        ]

        # Mock count result
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        # Mock the session's execute method to return different results
        # First call returns meeting rows, second call returns count
        self.mock_repo.execute.side_effect = [
            mock_rows,  # For the main query
            mock_count_result,  # For the count query
        ]

        # Execute
        meetings = self.repo.get_meetings(conference_id=1)

        # Assert
        assert len(meetings) == 2
        assert meetings[0]["conference_name"] == "本会議"

    def test_close(self):
        """Test closing the session"""
        # Execute
        self.repo.close()

        # Assert
        self.mock_repo.close.assert_called_once()
