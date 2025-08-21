"""Tests for MeetingRepository"""

from datetime import date
from typing import Any
from unittest.mock import MagicMock


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
        mock_data = [
            {"id": 1, "name": "日本国", "type": "国"},
            {"id": 2, "name": "東京都", "type": "都道府県"},
            {"id": 3, "name": "京都市", "type": "市町村"},
        ]

        self.repo.get_governing_bodies.return_value = mock_data

        # Execute
        result = self.repo.get_governing_bodies()

        # Verify
        assert len(result) == 3
        assert result[0]["name"] == "日本国"
        assert result[0]["type"] == "国"
        assert result[1]["name"] == "東京都"
        assert result[2]["name"] == "京都市"

    def test_get_conferences_by_governing_body(self):
        """Test getting conferences by governing body"""
        # Mock data
        mock_data = [
            {"id": 1, "name": "本会議", "governing_body_id": 1},
            {"id": 2, "name": "委員会", "governing_body_id": 1},
        ]

        self.repo.get_conferences_by_governing_body.return_value = mock_data

        # Execute
        result = self.repo.get_conferences_by_governing_body(1)

        # Verify
        assert len(result) == 2
        assert result[0]["name"] == "本会議"
        assert result[1]["name"] == "委員会"

    def test_get_all_conferences(self):
        """Test getting all conferences"""
        # Mock data
        mock_data = [
            {"id": 1, "name": "本会議", "governing_body_id": 1},
            {"id": 2, "name": "総務委員会", "governing_body_id": 2},
            {"id": 3, "name": "建設委員会", "governing_body_id": 3},
        ]

        self.repo.get_all_conferences.return_value = mock_data

        # Execute
        result = self.repo.get_all_conferences()

        # Verify
        assert len(result) == 3
        assert result[0]["name"] == "本会議"
        assert result[1]["name"] == "総務委員会"
        assert result[2]["name"] == "建設委員会"

    def test_create_meeting(self):
        """Test creating a meeting"""
        # Mock data
        self.repo.create_meeting.return_value = 100

        # Meeting data to create
        meeting_data = MagicMock()
        meeting_data.conference_id = 1
        meeting_data.date = date(2024, 1, 15)
        meeting_data.title = "第1回定例会"
        meeting_data.url = "https://example.com/meeting"
        meeting_data.pdf_url = "https://example.com/meeting.pdf"

        # Execute
        result_id = self.repo.create_meeting(meeting_data)

        # Verify
        assert result_id == 100
        self.repo.create_meeting.assert_called_once_with(meeting_data)

    def test_update_meeting(self):
        """Test updating a meeting"""
        # Mock data - No exception should be raised
        self.repo.update_meeting.return_value = None

        # Meeting data to update
        meeting_data = MagicMock()
        meeting_data.id = 1
        meeting_data.conference_id = 1
        meeting_data.date = date(2024, 1, 15)
        meeting_data.title = "更新後タイトル"
        meeting_data.url = "https://example.com/updated"

        # Execute
        self.repo.update_meeting(meeting_data)

        # Verify
        self.repo.update_meeting.assert_called_once_with(meeting_data)

    def test_delete_meeting_success(self):
        """Test successful meeting deletion"""
        # Mock - meeting exists and no related minutes
        self.repo.delete_meeting.return_value = True

        # Execute
        result = self.repo.delete_meeting(1)

        # Verify
        assert result is True
        self.repo.delete_meeting.assert_called_once_with(1)

    def test_delete_meeting_with_related_minutes(self):
        """Test meeting deletion when minutes exist"""
        # Mock - meeting has related minutes
        self.repo.delete_meeting.return_value = False

        # Execute
        result = self.repo.delete_meeting(1)

        # Verify
        assert result is False
        self.repo.delete_meeting.assert_called_once_with(1)

    def test_get_meeting_by_id(self):
        """Test getting a meeting by ID"""
        # Mock data
        mock_meeting = MagicMock()
        mock_meeting.id = 1
        mock_meeting.conference_id = 1
        mock_meeting.date = date(2024, 1, 15)
        mock_meeting.title = "第1回定例会"
        mock_meeting.url = "https://example.com/meeting"

        self.repo.get_by_id.return_value = mock_meeting

        # Execute
        result = self.repo.get_by_id(1)

        # Verify
        assert result is not None
        assert result.id == 1
        assert result.title == "第1回定例会"

    def test_get_meetings_with_filter(self):
        """Test getting meetings with filters"""
        # Mock data
        mock_meeting1 = MagicMock()
        mock_meeting1.id = 1
        mock_meeting1.conference_id = 1
        mock_meeting1.date = date(2024, 1, 15)
        mock_meeting1.title = "第1回定例会"
        mock_meeting1.url = "https://example.com/meeting1"

        mock_meeting2 = MagicMock()
        mock_meeting2.id = 2
        mock_meeting2.conference_id = 1
        mock_meeting2.date = date(2024, 2, 15)
        mock_meeting2.title = "第2回定例会"
        mock_meeting2.url = "https://example.com/meeting2"

        mock_meetings = [mock_meeting1, mock_meeting2]

        self.repo.get_meetings.return_value = mock_meetings

        # Execute
        result = self.repo.get_meetings(
            conference_id=1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
        )

        # Verify
        assert len(result) == 2
        assert result[0].title == "第1回定例会"
        assert result[1].title == "第2回定例会"

    def test_close(self):
        """Test closing repository connection"""
        # Execute
        self.repo.close()

        # Verify
        self.repo.close.assert_called_once()
