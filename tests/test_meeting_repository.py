"""Tests for MeetingRepository"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import date
from src.database.meeting_repository import MeetingRepository


class TestMeetingRepository:
    """Test cases for MeetingRepository"""
    
    @patch('src.database.meeting_repository.get_db_session')
    def setup_method(self, method, mock_get_db_session):
        """Set up test fixtures"""
        self.mock_session = MagicMock()
        mock_get_db_session.return_value = self.mock_session
        self.repo = MeetingRepository()
    
    def test_get_governing_bodies(self):
        """Test getting all governing bodies"""
        # Mock data
        mock_result = [
            (1, '日本国', '国'),
            (2, '東京都', '都道府県'),
            (3, '京都市', '市町村')
        ]
        self.mock_session.execute.return_value = mock_result
        
        # Execute
        result = self.repo.get_governing_bodies()
        
        # Assert
        assert len(result) == 3
        assert result[0] == {"id": 1, "name": "日本国", "type": "国"}
        assert result[1] == {"id": 2, "name": "東京都", "type": "都道府県"}
        
    def test_get_conferences_by_governing_body(self):
        """Test getting conferences by governing body"""
        # Mock data
        mock_result = [
            (1, '本会議', '議院'),
            (2, '予算委員会', '常任委員会')
        ]
        self.mock_session.execute.return_value = mock_result
        
        # Execute
        result = self.repo.get_conferences_by_governing_body(1)
        
        # Assert
        assert len(result) == 2
        assert result[0] == {"id": 1, "name": "本会議", "type": "議院"}
        
    def test_get_all_conferences(self):
        """Test getting all conferences with governing bodies"""
        # Mock data
        mock_result = [
            (1, '本会議', '議院', 1, '日本国', '国'),
            (2, '市議会', '地方議会全体', 3, '京都市', '市町村')
        ]
        self.mock_session.execute.return_value = mock_result
        
        # Execute
        result = self.repo.get_all_conferences()
        
        # Assert
        assert len(result) == 2
        assert result[0]["name"] == "本会議"
        assert result[0]["governing_body_name"] == "日本国"
        assert result[1]["governing_body_type"] == "市町村"
        
    def test_create_meeting(self):
        """Test creating a new meeting"""
        # Mock data
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (123,)
        self.mock_session.execute.return_value = mock_result
        
        # Execute
        meeting_id = self.repo.create_meeting(
            conference_id=1,
            meeting_date=date(2024, 6, 1),
            url="https://example.com/meeting.pdf"
        )
        
        # Assert
        assert meeting_id == 123
        self.mock_session.commit.assert_called_once()
        
    def test_update_meeting(self):
        """Test updating a meeting"""
        # Mock data
        mock_result = MagicMock()
        mock_result.rowcount = 1
        self.mock_session.execute.return_value = mock_result
        
        # Execute
        success = self.repo.update_meeting(
            meeting_id=1,
            meeting_date=date(2024, 6, 2),
            url="https://example.com/updated.pdf"
        )
        
        # Assert
        assert success is True
        self.mock_session.commit.assert_called_once()
        
    def test_delete_meeting_success(self):
        """Test deleting a meeting successfully"""
        # Mock data - no related minutes
        check_result = MagicMock()
        check_result.fetchone.return_value = (0,)
        
        delete_result = MagicMock()
        delete_result.rowcount = 1
        
        self.mock_session.execute.side_effect = [check_result, delete_result]
        
        # Execute
        success = self.repo.delete_meeting(1)
        
        # Assert
        assert success is True
        self.mock_session.commit.assert_called_once()
        
    def test_delete_meeting_with_related_minutes(self):
        """Test deleting a meeting with related minutes"""
        # Mock data - has related minutes
        check_result = MagicMock()
        check_result.fetchone.return_value = (2,)
        
        self.mock_session.execute.return_value = check_result
        
        # Execute
        success = self.repo.delete_meeting(1)
        
        # Assert
        assert success is False
        self.mock_session.commit.assert_not_called()
        
    def test_get_meeting_by_id(self):
        """Test getting a meeting by ID"""
        # Mock data
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (
            1, 2, date(2024, 6, 1), "https://example.com/meeting.pdf",
            "本会議", 1, "日本国"
        )
        self.mock_session.execute.return_value = mock_result
        
        # Execute
        meeting = self.repo.get_meeting_by_id(1)
        
        # Assert
        assert meeting is not None
        assert meeting["id"] == 1
        assert meeting["conference_name"] == "本会議"
        assert meeting["governing_body_name"] == "日本国"
        
    def test_get_meetings_with_filter(self):
        """Test getting meetings with conference filter"""
        # Mock data
        mock_result = [
            (1, date(2024, 6, 1), "https://example.com/1.pdf", "本会議", "日本国"),
            (2, date(2024, 5, 15), "https://example.com/2.pdf", "本会議", "日本国")
        ]
        self.mock_session.execute.return_value = mock_result
        
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
        self.mock_session.close.assert_called_once()