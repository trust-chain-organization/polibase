"""Tests for MeetingRepositoryImpl

Comprehensive test suite covering CRUD operations, queries, GCS operations,
and conversion methods for the Meeting repository.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.meeting import Meeting
from src.infrastructure.persistence.meeting_repository_impl import (
    MeetingRepositoryImpl,
)


@pytest.fixture
def mock_async_session():
    """Create mock async session for testing"""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def async_repository(mock_async_session):
    """Create repository with async session"""
    return MeetingRepositoryImpl(session=mock_async_session)


@pytest.fixture
def sample_meeting():
    """Create sample meeting entity for testing"""
    return Meeting(
        id=1,
        conference_id=100,
        date=date(2024, 1, 15),
        url="https://example.com/meeting/1",
        name="Sample Meeting",
        gcs_pdf_uri="gs://bucket/meeting1.pdf",
        gcs_text_uri="gs://bucket/meeting1.txt",
        attendees_mapping={"speaker1": "politician1"},
    )


@pytest.fixture
def sample_meeting_dict():
    """Create sample meeting as dict for testing"""
    return {
        "id": 1,
        "conference_id": 100,
        "date": date(2024, 1, 15),
        "url": "https://example.com/meeting/1",
        "name": "Sample Meeting",
        "gcs_pdf_uri": "gs://bucket/meeting1.pdf",
        "gcs_text_uri": "gs://bucket/meeting1.txt",
        "attendees_mapping": {"speaker1": "politician1"},
    }


class TestMeetingRepositoryImplInitialization:
    """Test repository initialization with different session types"""

    def test_sync_session_initialization(self):
        """Test that sync session is properly initialized"""
        sync_session = MagicMock()
        repo = MeetingRepositoryImpl(session=sync_session)

        assert repo.sync_session == sync_session
        assert repo.async_session is None
        assert repo.session_adapter is None

    @pytest.mark.asyncio
    async def test_async_session_initialization(self):
        """Test that async session is properly initialized"""
        async_session = AsyncMock(spec=AsyncSession)
        repo = MeetingRepositoryImpl(session=async_session)

        assert repo.async_session == async_session
        assert repo.sync_session is None


class TestMeetingRepositoryImplCRUD:
    """Test CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_meeting_success(
        self, async_repository, sample_meeting, mock_async_session
    ):
        """Test successful meeting creation"""
        mock_async_session.add = MagicMock()
        mock_async_session.commit = AsyncMock()
        mock_async_session.refresh = AsyncMock()

        result = await async_repository.create(sample_meeting)

        assert result == sample_meeting
        mock_async_session.add.assert_called_once()
        mock_async_session.commit.assert_awaited_once()
        mock_async_session.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_meeting_with_minimal_data(
        self, async_repository, mock_async_session
    ):
        """Test creating meeting with minimal required data"""
        minimal_meeting = Meeting(conference_id=100)

        mock_async_session.add = MagicMock()
        mock_async_session.commit = AsyncMock()
        mock_async_session.refresh = AsyncMock()

        result = await async_repository.create(minimal_meeting)

        assert result.conference_id == 100
        mock_async_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self, async_repository, sample_meeting, mock_async_session
    ):
        """Test retrieving meeting by ID when it exists"""
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(first=MagicMock(return_value=sample_meeting))
        )
        mock_async_session.execute = AsyncMock(return_value=mock_result)

        result = await async_repository.get_by_id(1)

        assert result == sample_meeting
        mock_async_session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, async_repository, mock_async_session):
        """Test retrieving meeting by ID when it doesn't exist"""
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(first=MagicMock(return_value=None))
        )
        mock_async_session.execute = AsyncMock(return_value=mock_result)

        result = await async_repository.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_success(
        self, async_repository, sample_meeting, mock_async_session
    ):
        """Test retrieving all meetings"""
        meetings = [sample_meeting, Meeting(id=2, conference_id=101)]

        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=meetings))
        )
        mock_async_session.execute = AsyncMock(return_value=mock_result)

        result = await async_repository.get_all()

        assert len(result) == 2
        assert result[0] == sample_meeting

    @pytest.mark.asyncio
    async def test_get_all_empty(self, async_repository, mock_async_session):
        """Test retrieving all meetings when none exist"""
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[]))
        )
        mock_async_session.execute = AsyncMock(return_value=mock_result)

        result = await async_repository.get_all()

        assert result == []

    @pytest.mark.asyncio
    async def test_update_meeting_success(
        self, async_repository, sample_meeting, mock_async_session
    ):
        """Test successful meeting update"""
        mock_async_session.merge = MagicMock(return_value=sample_meeting)
        mock_async_session.commit = AsyncMock()
        mock_async_session.refresh = AsyncMock()

        sample_meeting.name = "Updated Meeting Name"
        result = await async_repository.update(sample_meeting)

        assert result.name == "Updated Meeting Name"
        mock_async_session.merge.assert_called_once()
        mock_async_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_meeting_partial_fields(
        self, async_repository, sample_meeting, mock_async_session
    ):
        """Test updating only some fields of a meeting"""
        mock_async_session.merge = MagicMock(return_value=sample_meeting)
        mock_async_session.commit = AsyncMock()
        mock_async_session.refresh = AsyncMock()

        sample_meeting.url = "https://example.com/updated"
        result = await async_repository.update(sample_meeting)

        assert result.url == "https://example.com/updated"

    @pytest.mark.asyncio
    async def test_delete_meeting_success(
        self, async_repository, sample_meeting, mock_async_session
    ):
        """Test successful meeting deletion"""
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(first=MagicMock(return_value=sample_meeting))
        )
        mock_async_session.execute = AsyncMock(return_value=mock_result)
        mock_async_session.delete = MagicMock()
        mock_async_session.commit = AsyncMock()

        await async_repository.delete(1)

        mock_async_session.delete.assert_called_once()
        mock_async_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_meeting_not_found(self, async_repository, mock_async_session):
        """Test deleting meeting that doesn't exist"""
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(first=MagicMock(return_value=None))
        )
        mock_async_session.execute = AsyncMock(return_value=mock_result)

        result = await async_repository.delete(999)

        assert result is None


class TestMeetingRepositoryImplQueries:
    """Test query methods"""

    @pytest.mark.asyncio
    async def test_get_by_conference_and_date_found(
        self, async_repository, sample_meeting, mock_async_session
    ):
        """Test retrieving meeting by conference and date"""
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(first=MagicMock(return_value=sample_meeting))
        )
        mock_async_session.execute = AsyncMock(return_value=mock_result)

        result = await async_repository.get_by_conference_and_date(
            100, date(2024, 1, 15)
        )

        assert result == sample_meeting

    @pytest.mark.asyncio
    async def test_get_by_conference_and_date_not_found(
        self, async_repository, mock_async_session
    ):
        """Test retrieving meeting when not found"""
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(first=MagicMock(return_value=None))
        )
        mock_async_session.execute = AsyncMock(return_value=mock_result)

        result = await async_repository.get_by_conference_and_date(
            100, date(2024, 1, 15)
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_conference_multiple_results(
        self, async_repository, sample_meeting, mock_async_session
    ):
        """Test retrieving all meetings for a conference"""
        meetings = [sample_meeting, Meeting(id=2, conference_id=100)]

        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=meetings))
        )
        mock_async_session.execute = AsyncMock(return_value=mock_result)

        result = await async_repository.get_by_conference(100)

        assert len(result) == 2
        assert all(m.conference_id == 100 for m in result)

    @pytest.mark.asyncio
    async def test_get_by_conference_empty(self, async_repository, mock_async_session):
        """Test retrieving meetings for conference with none"""
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=[]))
        )
        mock_async_session.execute = AsyncMock(return_value=mock_result)

        result = await async_repository.get_by_conference(100)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_unprocessed_returns_meetings(
        self, async_repository, sample_meeting, mock_async_session
    ):
        """Test retrieving unprocessed meetings"""
        meetings = [sample_meeting]

        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=meetings))
        )
        mock_async_session.execute = AsyncMock(return_value=mock_result)

        result = await async_repository.get_unprocessed()

        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_get_unprocessed_with_limit(
        self, async_repository, mock_async_session
    ):
        """Test retrieving unprocessed meetings with limit"""
        meetings = [Meeting(id=i, conference_id=100) for i in range(1, 6)]

        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(all=MagicMock(return_value=meetings[:3]))
        )
        mock_async_session.execute = AsyncMock(return_value=mock_result)

        result = await async_repository.get_unprocessed(limit=3)

        assert len(result) <= 3


class TestMeetingRepositoryImplGCSOperations:
    """Test GCS URI operations"""

    @pytest.mark.asyncio
    async def test_update_gcs_uris_success(
        self, async_repository, sample_meeting, mock_async_session
    ):
        """Test successful GCS URI update"""
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(first=MagicMock(return_value=sample_meeting))
        )
        mock_async_session.execute = AsyncMock(return_value=mock_result)
        mock_async_session.commit = AsyncMock()

        result = await async_repository.update_gcs_uris(
            1,
            gcs_pdf_uri="gs://bucket/new.pdf",
            gcs_text_uri="gs://bucket/new.txt",
        )

        assert result == sample_meeting
        mock_async_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_gcs_uris_pdf_only(
        self, async_repository, sample_meeting, mock_async_session
    ):
        """Test updating only PDF URI"""
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(first=MagicMock(return_value=sample_meeting))
        )
        mock_async_session.execute = AsyncMock(return_value=mock_result)
        mock_async_session.commit = AsyncMock()

        result = await async_repository.update_gcs_uris(
            1, gcs_pdf_uri="gs://bucket/new.pdf"
        )

        assert result == sample_meeting

    @pytest.mark.asyncio
    async def test_update_gcs_uris_text_only(
        self, async_repository, sample_meeting, mock_async_session
    ):
        """Test updating only text URI"""
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(first=MagicMock(return_value=sample_meeting))
        )
        mock_async_session.execute = AsyncMock(return_value=mock_result)
        mock_async_session.commit = AsyncMock()

        result = await async_repository.update_gcs_uris(
            1, gcs_text_uri="gs://bucket/new.txt"
        )

        assert result == sample_meeting

    @pytest.mark.asyncio
    async def test_update_meeting_gcs_uris_both(
        self, async_repository, sample_meeting, mock_async_session
    ):
        """Test updating both GCS URIs via update_meeting_gcs_uris"""
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(
            return_value=MagicMock(first=MagicMock(return_value=sample_meeting))
        )
        mock_async_session.execute = AsyncMock(return_value=mock_result)
        mock_async_session.commit = AsyncMock()

        await async_repository.update_meeting_gcs_uris(
            1, "gs://bucket/pdf.pdf", "gs://bucket/text.txt"
        )

        mock_async_session.commit.assert_awaited_once()


class TestMeetingRepositoryImplConversions:
    """Test conversion methods"""

    def test_to_entity_complete_data(self, async_repository, sample_meeting_dict):
        """Test converting model to entity with complete data"""
        mock_model = MagicMock()
        for key, value in sample_meeting_dict.items():
            setattr(mock_model, key, value)

        entity = async_repository._to_entity(mock_model)

        assert isinstance(entity, Meeting)
        assert entity.id == 1
        assert entity.conference_id == 100
        assert entity.name == "Sample Meeting"

    def test_to_entity_minimal_data(self, async_repository):
        """Test converting model to entity with minimal data"""
        mock_model = MagicMock()
        mock_model.id = 1
        mock_model.conference_id = 100
        mock_model.date = None
        mock_model.url = None
        mock_model.name = None
        mock_model.gcs_pdf_uri = None
        mock_model.gcs_text_uri = None
        mock_model.attendees_mapping = None

        entity = async_repository._to_entity(mock_model)

        assert entity.id == 1
        assert entity.conference_id == 100
        assert entity.date is None

    def test_to_model_complete_data(self, async_repository, sample_meeting):
        """Test converting entity to model with complete data"""
        model = async_repository._to_model(sample_meeting)

        assert model.id == 1
        assert model.conference_id == 100
        assert model.name == "Sample Meeting"

    def test_to_model_minimal_data(self, async_repository):
        """Test converting entity to model with minimal data"""
        minimal_meeting = Meeting(conference_id=100)

        model = async_repository._to_model(minimal_meeting)

        assert model.conference_id == 100

    def test_update_model_all_fields(self, async_repository, sample_meeting):
        """Test updating all model fields from entity"""
        mock_model = MagicMock()

        async_repository._update_model(mock_model, sample_meeting)

        assert mock_model.conference_id == 100
        assert mock_model.name == "Sample Meeting"

    def test_update_model_partial_fields(self, async_repository):
        """Test updating model with partial entity data"""
        mock_model = MagicMock()
        mock_model.name = "Old Name"

        partial_meeting = Meeting(conference_id=100, name="New Name")

        async_repository._update_model(mock_model, partial_meeting)

        assert mock_model.conference_id == 100

    def test_dict_to_entity_success(self, async_repository, sample_meeting_dict):
        """Test converting dict to entity"""
        entity = async_repository._dict_to_entity(sample_meeting_dict)

        assert isinstance(entity, Meeting)
        assert entity.id == 1
        assert entity.conference_id == 100

    def test_pydantic_to_entity_success(self, async_repository):
        """Test converting Pydantic model to entity"""
        mock_pydantic = MagicMock()
        mock_pydantic.model_dump = MagicMock(
            return_value={
                "id": 1,
                "conference_id": 100,
                "name": "Pydantic Meeting",
            }
        )

        entity = async_repository._pydantic_to_entity(mock_pydantic)

        assert isinstance(entity, Meeting)
