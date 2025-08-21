"""Parliamentary group membership repository implementation

This is a stub implementation for compatibility during migration.
The actual functionality is still in the legacy repository.
"""

from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class ParliamentaryGroupMembershipRepositoryImpl:
    """Parliamentary group membership repository stub implementation

    This is a minimal implementation to satisfy imports during the migration
    from legacy repositories to Clean Architecture.
    """

    def __init__(self, session: AsyncSession | None = None):
        """Initialize repository

        Args:
            session: Async database session (optional)
        """
        self.session = session

    async def get_by_group(self, group_id: int) -> list[dict[str, Any]]:
        """Get memberships by group (stub)"""
        return []

    async def get_by_politician(self, politician_id: int) -> list[dict[str, Any]]:
        """Get memberships by politician (stub)"""
        return []

    async def get_active_by_group(
        self, group_id: int, as_of_date: date | None = None
    ) -> list[dict[str, Any]]:
        """Get active memberships by group (stub)"""
        return []

    async def create_membership(
        self,
        politician_id: int,
        group_id: int,
        start_date: date,
        role: str | None = None,
    ) -> dict[str, Any]:
        """Create a new membership (stub)"""
        return {
            "id": 0,
            "politician_id": politician_id,
            "parliamentary_group_id": group_id,
            "start_date": start_date,
            "role": role,
        }

    async def end_membership(
        self, membership_id: int, end_date: date
    ) -> dict[str, Any] | None:
        """End a membership (stub)"""
        return None

    async def delete_by_group(self, group_id: int) -> int:
        """Delete all memberships for a group (stub)"""
        return 0
