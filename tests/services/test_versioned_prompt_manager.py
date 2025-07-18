"""Tests for VersionedPromptManager."""

# pyright: reportPrivateUsage=false
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.domain.entities.prompt_version import PromptVersion
from src.services.versioned_prompt_manager import VersionedPromptManager


@pytest.fixture
def mock_repository():
    """Create a mock prompt version repository."""
    return AsyncMock()


@pytest.fixture
def manager_with_repo(mock_repository):
    """Create a versioned prompt manager with repository."""
    return VersionedPromptManager(repository=mock_repository)


@pytest.fixture
def manager_without_repo():
    """Create a versioned prompt manager without repository."""
    return VersionedPromptManager(repository=None)


class TestVersionedPromptManager:
    """Test cases for VersionedPromptManager."""

    @pytest.mark.asyncio
    async def test_get_versioned_prompt_with_repo(
        self, manager_with_repo, mock_repository
    ):
        """Test getting versioned prompt with repository."""
        # Setup
        prompt_version = PromptVersion(
            prompt_key="test_prompt",
            template="Hello {name}!",
            version="1.0.0",
            variables=["name"],
            is_active=True,
            id=1,
        )
        mock_repository.get_active_version.return_value = prompt_version

        # Execute
        result, version = await manager_with_repo.get_versioned_prompt(
            "test_prompt", {"name": "Alice"}
        )

        # Assert
        assert result == "Hello Alice!"
        assert version == "1.0.0"
        mock_repository.get_active_version.assert_called_once_with("test_prompt")

    @pytest.mark.asyncio
    async def test_get_versioned_prompt_fallback_to_legacy(
        self, manager_with_repo, mock_repository
    ):
        """Test falling back to legacy prompt when versioned not found."""
        # Setup
        mock_repository.get_active_version.return_value = None

        # Execute
        result, version = await manager_with_repo.get_versioned_prompt(
            "minutes_divide", {"minutes": "Test minutes"}
        )

        # Assert
        assert "議事録を分析し" in result
        assert "Test minutes" in result
        assert version == "legacy"

    @pytest.mark.asyncio
    async def test_get_versioned_prompt_without_repo(self, manager_without_repo):
        """Test getting prompt without repository falls back to legacy."""
        # Execute
        result, version = await manager_without_repo.get_versioned_prompt(
            "speaker_match", {"speaker_name": "Test", "available_speakers": "List"}
        )

        # Assert
        assert "議事録の発言者名マッチング専門家" in result
        assert version == "legacy"

    @pytest.mark.asyncio
    async def test_get_versioned_prompt_missing_variables(
        self, manager_with_repo, mock_repository
    ):
        """Test getting versioned prompt with missing variables raises error."""
        # Setup
        prompt_version = PromptVersion(
            prompt_key="test_prompt",
            template="Hello {name} from {city}!",
            version="1.0.0",
            variables=["name", "city"],
            is_active=True,
        )
        mock_repository.get_active_version.return_value = prompt_version

        # Execute & Assert
        with pytest.raises(ValueError, match="Missing required variables"):
            await manager_with_repo.get_versioned_prompt(
                "test_prompt", {"name": "Alice"}
            )

    @pytest.mark.asyncio
    async def test_get_active_version_with_cache(
        self, manager_with_repo, mock_repository
    ):
        """Test getting active version uses cache."""
        # Setup
        prompt_version = PromptVersion(
            prompt_key="test_prompt",
            template="Test",
            version="1.0.0",
            is_active=True,
        )
        prompt_version.updated_at = datetime.now()
        mock_repository.get_active_version.return_value = prompt_version

        # First call - should hit repository
        result1 = await manager_with_repo._get_active_version("test_prompt")
        assert result1 == prompt_version
        assert mock_repository.get_active_version.call_count == 1

        # Second call - should use cache
        result2 = await manager_with_repo._get_active_version("test_prompt")
        assert result2 == prompt_version
        assert mock_repository.get_active_version.call_count == 1  # No additional calls

    @pytest.mark.asyncio
    async def test_get_active_version_cache_expiry(
        self, manager_with_repo, mock_repository
    ):
        """Test cache expires after 5 minutes."""
        # Setup
        prompt_version = PromptVersion(
            prompt_key="test_prompt",
            template="Test",
            version="1.0.0",
            is_active=True,
        )
        # Set updated_at to more than 5 minutes ago
        prompt_version.updated_at = datetime.now() - timedelta(minutes=6)

        # Add to cache
        manager_with_repo._version_cache["test_prompt"] = prompt_version
        mock_repository.get_active_version.return_value = prompt_version

        # Execute - should hit repository due to cache expiry
        result = await manager_with_repo._get_active_version("test_prompt")

        # Assert
        assert result == prompt_version
        mock_repository.get_active_version.assert_called_once_with("test_prompt")

    @pytest.mark.asyncio
    async def test_get_active_version_error_handling(
        self, manager_with_repo, mock_repository
    ):
        """Test error handling when fetching active version."""
        # Setup
        mock_repository.get_active_version.side_effect = Exception("DB Error")

        # Execute
        result = await manager_with_repo._get_active_version("test_prompt")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_save_prompt_version_success(
        self, manager_with_repo, mock_repository
    ):
        """Test saving a new prompt version."""
        # Setup
        created_version = PromptVersion(
            prompt_key="new_prompt",
            template="New template",
            version="2.0.0",
            is_active=True,
        )
        mock_repository.create_version.return_value = created_version

        # Execute
        result = await manager_with_repo.save_new_version(
            prompt_key="new_prompt",
            template="New template",
            version="2.0.0",
            description="New version",
            created_by="test_user",
        )

        # Assert
        assert result == created_version
        mock_repository.create_version.assert_called_once()
        assert manager_with_repo._version_cache.get("new_prompt") == created_version

    @pytest.mark.asyncio
    async def test_save_prompt_version_auto_version(
        self, manager_with_repo, mock_repository
    ):
        """Test auto-generating version when not provided."""
        # Setup
        created_version = PromptVersion(
            prompt_key="test",
            template="Test",
            version="20231225-123456",
            is_active=True,
        )
        mock_repository.create_version.return_value = created_version

        # Execute
        with patch("src.services.versioned_prompt_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "20231225-123456"
            result = await manager_with_repo.save_new_version(
                prompt_key="test",
                template="Test",
            )

        # Assert
        assert result is not None
        call_args = mock_repository.create_version.call_args[1]
        assert call_args["version"] == "20231225-123456"

    @pytest.mark.asyncio
    async def test_save_prompt_version_without_repo(self, manager_without_repo):
        """Test saving prompt version without repository returns None."""
        # Execute
        result = await manager_without_repo.save_new_version(
            prompt_key="test",
            template="Test",
        )

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_save_prompt_version_error_handling(
        self, manager_with_repo, mock_repository
    ):
        """Test error handling when saving prompt version."""
        # Setup
        mock_repository.create_version.side_effect = Exception("Save failed")

        # Execute & Assert
        with pytest.raises(Exception, match="Save failed"):
            await manager_with_repo.save_new_version(
                prompt_key="test",
                template="Test",
            )

    @pytest.mark.asyncio
    async def test_get_prompt_history(self, manager_with_repo, mock_repository):
        """Test getting prompt history."""
        # Setup
        versions = [
            PromptVersion(prompt_key="test", template="v1", version="1.0.0"),
            PromptVersion(prompt_key="test", template="v2", version="2.0.0"),
        ]
        mock_repository.get_versions_by_key.return_value = versions

        # Execute
        result = await manager_with_repo.get_prompt_history("test", limit=10)

        # Assert
        assert result == versions
        mock_repository.get_versions_by_key.assert_called_once_with("test", 10)

    @pytest.mark.asyncio
    async def test_get_prompt_history_without_repo(self, manager_without_repo):
        """Test getting prompt history without repository returns empty list."""
        # Execute
        result = await manager_without_repo.get_prompt_history("test")

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_activate_version_success(self, manager_with_repo, mock_repository):
        """Test activating a specific version."""
        # Setup
        mock_repository.activate_version.return_value = True
        manager_with_repo._version_cache["test"] = Mock()  # Add to cache

        # Execute
        result = await manager_with_repo.activate_version("test", "2.0.0")

        # Assert
        assert result is True
        mock_repository.activate_version.assert_called_once_with("test", "2.0.0")
        assert "test" not in manager_with_repo._version_cache  # Cache cleared

    @pytest.mark.asyncio
    async def test_activate_version_failure(self, manager_with_repo, mock_repository):
        """Test activating version that doesn't exist."""
        # Setup
        mock_repository.activate_version.return_value = False

        # Execute
        result = await manager_with_repo.activate_version("test", "999.0.0")

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_get_specific_version(self, manager_with_repo, mock_repository):
        """Test getting a specific version of a prompt."""
        # Setup
        version = PromptVersion(
            prompt_key="test",
            template="Specific version",
            version="2.5.0",
        )
        mock_repository.get_by_key_and_version.return_value = version

        # Execute
        result = await manager_with_repo.get_specific_version("test", "2.5.0")

        # Assert
        assert result == version
        mock_repository.get_by_key_and_version.assert_called_once_with("test", "2.5.0")

    @pytest.mark.asyncio
    async def test_migrate_existing_prompts(self, manager_with_repo, mock_repository):
        """Test migrating existing static prompts."""
        # Setup
        # Mock save_prompt_version to track calls
        saved_prompts = []

        async def mock_save(prompt_key, **kwargs):
            saved_prompts.append(prompt_key)
            return Mock()

        manager_with_repo.save_new_version = mock_save

        # Execute
        count = await manager_with_repo.migrate_existing_prompts("system")

        # Assert
        assert count == len(manager_with_repo.PROMPTS)
        assert "minutes_divide" in saved_prompts
        assert "speaker_match" in saved_prompts

    @pytest.mark.asyncio
    async def test_migrate_existing_prompts_partial_failure(self, manager_with_repo):
        """Test migration continues even if some prompts fail."""
        # Setup
        call_count = 0

        async def mock_save(prompt_key, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Fail on second prompt
                raise Exception("Migration failed")
            return Mock()

        manager_with_repo.save_new_version = mock_save

        # Execute
        count = await manager_with_repo.migrate_existing_prompts("system")

        # Assert
        assert count == len(manager_with_repo.PROMPTS) - 1  # One less due to failure

    def test_clear_cache(self, manager_with_repo):
        """Test clearing the version cache."""
        # Setup
        manager_with_repo._version_cache = {
            "test1": Mock(),
            "test2": Mock(),
        }

        # Execute
        manager_with_repo.clear_cache()

        # Assert
        assert manager_with_repo._version_cache == {}
