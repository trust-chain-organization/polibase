"""Prompt version repository interface."""

from abc import abstractmethod
from typing import Any

from src.domain.entities.prompt_version import PromptVersion
from src.domain.repositories.base import BaseRepository


class PromptVersionRepository(BaseRepository[PromptVersion]):
    """Repository interface for prompt versions."""

    @abstractmethod
    async def get_active_version(self, prompt_key: str) -> PromptVersion | None:
        """Get the currently active version for a prompt key.

        Args:
            prompt_key: The prompt identifier

        Returns:
            Active prompt version or None if not found
        """
        pass

    @abstractmethod
    async def get_by_key_and_version(
        self, prompt_key: str, version: str
    ) -> PromptVersion | None:
        """Get a specific version of a prompt.

        Args:
            prompt_key: The prompt identifier
            version: The version identifier

        Returns:
            Prompt version or None if not found
        """
        pass

    @abstractmethod
    async def get_versions_by_key(
        self, prompt_key: str, limit: int | None = None
    ) -> list[PromptVersion]:
        """Get all versions for a specific prompt key.

        Args:
            prompt_key: The prompt identifier
            limit: Maximum number of versions to return

        Returns:
            List of prompt versions ordered by created_at descending
        """
        pass

    @abstractmethod
    async def get_all_active_versions(self) -> list[PromptVersion]:
        """Get all active prompt versions.

        Returns:
            List of active prompt versions
        """
        pass

    @abstractmethod
    async def activate_version(self, prompt_key: str, version: str) -> bool:
        """Activate a specific version of a prompt.

        This will deactivate all other versions of the same prompt.

        Args:
            prompt_key: The prompt identifier
            version: The version to activate

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def deactivate_all_versions(self, prompt_key: str) -> int:
        """Deactivate all versions of a prompt.

        Args:
            prompt_key: The prompt identifier

        Returns:
            Number of versions deactivated
        """
        pass

    @abstractmethod
    async def create_version(
        self,
        prompt_key: str,
        template: str,
        version: str,
        description: str | None = None,
        variables: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        created_by: str | None = None,
        activate: bool = True,
    ) -> PromptVersion:
        """Create a new prompt version.

        Args:
            prompt_key: The prompt identifier
            template: The prompt template content
            version: Version identifier
            description: Optional description
            variables: List of variable names
            metadata: Additional metadata
            created_by: Creator identifier
            activate: Whether to activate this version immediately

        Returns:
            Created prompt version
        """
        pass

    @abstractmethod
    async def search(
        self,
        prompt_key: str | None = None,
        is_active: bool | None = None,
        created_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[PromptVersion]:
        """Search prompt versions with filters.

        Args:
            prompt_key: Filter by prompt key
            is_active: Filter by active status
            created_by: Filter by creator
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching prompt versions
        """
        pass
