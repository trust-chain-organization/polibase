"""Tests for MeetingRepositoryImpl"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.meeting import Meeting
from src.infrastructure.persistence.meeting_repository_impl import (
    MeetingModel,
    MeetingRepositoryImpl,
)


@pytest.mark.asyncio
class TestMeetingRepositoryImpl:
    """Test cases for MeetingRepositoryImpl"""

    def setup_method(self, method):
        """Set up test fixtures"""
        self.async_session = AsyncMock(spec=AsyncSession)
        self.repo = MeetingRepositoryImpl(session=self.async_session)

    async def test_get_by_conference_and_date(self):
        """Test getting meeting by conference and date"""
        # Mock data
        mock_model = MeetingModel(
            id=1,
            conference_id=123,
            date=date(2024, 6, 1),
            url="https://example.com/meeting.pdf",
            name="Test Meeting",
            gcs_pdf_uri="gs://bucket/pdf.pdf",
            gcs_text_uri="gs://bucket/text.txt",
        )

        # Mock the query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        self.async_session.execute.return_value = mock_result

        # Execute
        meeting = await self.repo.get_by_conference_and_date(123, date(2024, 6, 1))

        # Assert
        assert meeting is not None
        assert meeting.id == 1
        assert meeting.conference_id == 123
        assert meeting.date == date(2024, 6, 1)
        assert meeting.url == "https://example.com/meeting.pdf"

    async def test_get_by_conference(self):
        """Test getting meetings by conference"""
        # Mock data
        mock_models = [
            MeetingModel(
                id=1,
                conference_id=123,
                date=date(2024, 6, 1),
                url="https://example.com/1.pdf",
            ),
            MeetingModel(
                id=2,
                conference_id=123,
                date=date(2024, 5, 15),
                url="https://example.com/2.pdf",
            ),
        ]

        # Mock the query result
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_models
        mock_result.scalars.return_value = mock_scalars
        self.async_session.execute.return_value = mock_result

        # Execute
        meetings = await self.repo.get_by_conference(123, limit=10)

        # Assert
        assert len(meetings) == 2
        assert meetings[0].id == 1
        assert meetings[0].conference_id == 123
        assert meetings[1].id == 2

    async def test_get_unprocessed(self):
        """Test getting unprocessed meetings"""
        # Mock data
        mock_models = [
            MeetingModel(
                id=1,
                conference_id=123,
                date=date(2024, 6, 1),
                url="https://example.com/1.pdf",
            ),
            MeetingModel(
                id=2,
                conference_id=456,
                date=date(2024, 5, 15),
                url="https://example.com/2.pdf",
            ),
        ]

        # Mock the query result
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_models
        mock_result.scalars.return_value = mock_scalars
        self.async_session.execute.return_value = mock_result

        # Execute
        meetings = await self.repo.get_unprocessed(limit=5)

        # Assert
        assert len(meetings) == 2
        assert all(isinstance(m, Meeting) for m in meetings)

    async def test_update_gcs_uris(self):
        """Test updating GCS URIs"""
        # Mock the update result
        mock_result = MagicMock()
        mock_result.rowcount = 1
        self.async_session.execute.return_value = mock_result
        self.async_session.commit = AsyncMock()

        # Execute
        success = await self.repo.update_gcs_uris(
            1, pdf_uri="gs://bucket/new.pdf", text_uri="gs://bucket/new.txt"
        )

        # Assert
        assert success is True
        self.async_session.commit.assert_called_once()

    async def test_get_meetings_with_filters(self):
        """Test getting meetings with filters and pagination"""
        # Mock data
        mock_meetings = [
            {
                "id": 1,
                "conference_id": 123,
                "date": date(2024, 6, 1),
                "url": "https://example.com/1.pdf",
                "conference_name": "本会議",
                "governing_body_name": "日本国",
            },
            {
                "id": 2,
                "conference_id": 123,
                "date": date(2024, 5, 15),
                "url": "https://example.com/2.pdf",
                "conference_name": "本会議",
                "governing_body_name": "日本国",
            },
        ]

        # Mock meetings query
        mock_result = MagicMock()
        mock_rows = []
        for m in mock_meetings:
            mock_row = MagicMock()
            mock_row._mapping = m
            mock_rows.append(mock_row)
        mock_result.__iter__ = lambda self: iter(mock_rows)

        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        # Set up execute to return different results for different queries
        self.async_session.execute.side_effect = [mock_result, mock_count_result]

        # Execute
        meetings, total = await self.repo.get_meetings_with_filters(
            conference_id=123, limit=10, offset=0
        )

        # Assert
        assert len(meetings) == 2
        assert total == 2
        assert meetings[0]["conference_name"] == "本会議"

    async def test_get_meeting_by_id_with_info(self):
        """Test getting meeting by ID with full info"""
        # Mock data
        mock_row = MagicMock()
        mock_row._mapping = {
            "id": 1,
            "conference_id": 123,
            "date": date(2024, 6, 1),
            "url": "https://example.com/meeting.pdf",
            "conference_name": "本会議",
            "governing_body_name": "日本国",
        }

        # Mock the query result
        mock_result = MagicMock()
        mock_result.first.return_value = mock_row
        self.async_session.execute.return_value = mock_result

        # Execute
        meeting_info = await self.repo.get_meeting_by_id_with_info(1)

        # Assert
        assert meeting_info is not None
        assert meeting_info["id"] == 1
        assert meeting_info["conference_name"] == "本会議"

    async def test_create(self):
        """Test creating a meeting"""
        # Create a meeting entity
        meeting = Meeting(
            conference_id=123,
            date=date(2024, 6, 1),
            url="https://example.com/meeting.pdf",
            name="Test Meeting",
        )

        # Mock the session methods
        self.async_session.add = MagicMock()
        self.async_session.commit = AsyncMock()
        self.async_session.refresh = AsyncMock()

        # Execute
        created = await self.repo.create(meeting)

        # Assert
        assert created is not None
        assert created.conference_id == 123
        self.async_session.add.assert_called_once()
        self.async_session.commit.assert_called_once()

    async def test_update(self):
        """Test updating a meeting"""
        # Mock existing model
        mock_model = MeetingModel(
            id=1,
            conference_id=123,
            date=date(2024, 6, 1),
            url="https://example.com/old.pdf",
        )

        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        self.async_session.execute.return_value = mock_result
        self.async_session.commit = AsyncMock()

        # Create updated entity
        updated_meeting = Meeting(
            id=1,
            conference_id=123,
            date=date(2024, 6, 2),
            url="https://example.com/new.pdf",
        )

        # Execute
        result = await self.repo.update(updated_meeting)

        # Assert
        assert result is not None
        assert result.date == date(2024, 6, 2)
        assert result.url == "https://example.com/new.pdf"
        self.async_session.commit.assert_called_once()

    async def test_delete(self):
        """Test deleting a meeting"""
        # Mock existing model
        mock_model = MeetingModel(id=1, conference_id=123)

        # Mock query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        self.async_session.execute.return_value = mock_result
        self.async_session.delete = MagicMock()
        self.async_session.commit = AsyncMock()

        # Execute
        success = await self.repo.delete(1)

        # Assert
        assert success is True
        self.async_session.delete.assert_called_once_with(mock_model)
        self.async_session.commit.assert_called_once()


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
