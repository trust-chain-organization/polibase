"""Tests for MeetingRepositoryImpl with sync session"""

from unittest.mock import MagicMock

from src.infrastructure.persistence.meeting_repository_impl import MeetingRepositoryImpl


class TestMeetingRepositoryImplWithSyncSession:
    """Test cases for MeetingRepositoryImpl with sync session"""

    def setup_method(self, method):
        """Set up test fixtures"""
        self.sync_session = MagicMock()
        self.repo = MeetingRepositoryImpl(session=self.sync_session)

    def test_sync_session_initialization(self):
        """Test that sync session is properly initialized"""
        assert self.repo.sync_session == self.sync_session
        assert self.repo.async_session is None
        assert self.repo.legacy_repo is not None
