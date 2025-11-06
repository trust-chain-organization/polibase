"""Tests for UserRepositoryImpl."""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.user import User
from src.infrastructure.persistence.user_repository_impl import UserRepositoryImpl


class TestUserRepositoryImpl:
    """Test cases for UserRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> UserRepositoryImpl:
        """Create user repository."""
        return UserRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_user_id(self) -> UUID:
        """Sample user ID."""
        return uuid4()

    @pytest.fixture
    def sample_user_dict(self, sample_user_id: UUID) -> dict[str, Any]:
        """Sample user data as dict."""
        return {
            "user_id": sample_user_id,
            "email": "test@example.com",
            "name": "Test User",
            "picture": "https://example.com/picture.jpg",
            "created_at": datetime(2024, 1, 1, 0, 0, 0),
            "last_login_at": datetime(2024, 1, 15, 12, 0, 0),
        }

    @pytest.fixture
    def sample_user_entity(self, sample_user_id: UUID) -> User:
        """Sample user entity."""
        return User(
            user_id=sample_user_id,
            email="test@example.com",
            name="Test User",
            picture="https://example.com/picture.jpg",
            created_at=datetime(2024, 1, 1, 0, 0, 0),
            last_login_at=datetime(2024, 1, 15, 12, 0, 0),
        )

    @pytest.mark.asyncio
    async def test_get_by_id_found(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_id: UUID,
        sample_user_dict: dict[str, Any],
    ) -> None:
        """Test get_by_id when user is found."""
        # Setup mock result
        mock_row = MagicMock()
        for key, value in sample_user_dict.items():
            setattr(mock_row, key, value)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_id(sample_user_id)

        # Assert
        assert result is not None
        assert result.user_id == sample_user_id
        assert result.email == "test@example.com"
        assert result.name == "Test User"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_id when user is not found."""
        # Setup mock result
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_id(uuid4())

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_email_found(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_dict: dict[str, Any],
    ) -> None:
        """Test get_by_email when user is found."""
        # Setup mock result
        mock_row = MagicMock()
        for key, value in sample_user_dict.items():
            setattr(mock_row, key, value)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.get_by_email("test@example.com")

        # Assert
        assert result is not None
        assert result.email == "test@example.com"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_dict: dict[str, Any],
    ) -> None:
        """Test create user."""
        # Setup mock result
        mock_row = MagicMock()
        for key, value in sample_user_dict.items():
            setattr(mock_row, key, value)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute
        user = User(email="test@example.com", name="Test User")
        result = await repository.create(user)

        # Assert
        assert result is not None
        assert result.email == "test@example.com"
        assert result.name == "Test User"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_last_login(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_id: UUID,
    ) -> None:
        """Test update_last_login."""
        # Setup mock result
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Execute
        last_login = datetime.now()
        result = await repository.update_last_login(sample_user_id, last_login)

        # Assert
        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_count(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test count users."""
        # Setup mock result
        mock_row = MagicMock()
        mock_row.__getitem__ = MagicMock(return_value=5)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        # Execute
        result = await repository.count()

        # Assert
        assert result == 5
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_or_create_by_email_existing_user(
        self,
        repository: UserRepositoryImpl,
        mock_session: MagicMock,
        sample_user_dict: dict[str, Any],
    ) -> None:
        """Test find_or_create_by_email with existing user."""
        # Setup mock result for get_by_email
        mock_row = MagicMock()
        for key, value in sample_user_dict.items():
            setattr(mock_row, key, value)
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_result.rowcount = 1

        # Mock session to return user on first call (get_by_email)
        # and success on second call (update_last_login)
        mock_session.execute.side_effect = [mock_result, mock_result]

        # Execute
        result = await repository.find_or_create_by_email("test@example.com")

        # Assert
        assert result is not None
        assert result.email == "test@example.com"
        # Should call execute twice: get_by_email and update_last_login
        assert mock_session.execute.call_count >= 2
        mock_session.commit.assert_called()
