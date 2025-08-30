"""Parliamentary group membership repository implementation"""

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db_session


class ParliamentaryGroupMembershipRepositoryImpl:
    """Parliamentary group membership repository implementation"""

    def __init__(self, session: AsyncSession | None = None):
        """Initialize repository

        Args:
            session: Async database session (optional)
        """
        self.session = session

    async def get_by_group(self, group_id: int) -> list[dict[str, Any]]:
        """Get memberships by group"""
        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT * FROM parliamentary_group_memberships
                    WHERE parliamentary_group_id = :group_id
                """),
                {"group_id": group_id},
            )
            return [dict(row._mapping) for row in result]

    async def get_by_politician(self, politician_id: int) -> list[dict[str, Any]]:
        """Get memberships by politician"""
        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT * FROM parliamentary_group_memberships
                    WHERE politician_id = :politician_id
                """),
                {"politician_id": politician_id},
            )
            return [dict(row._mapping) for row in result]

    async def get_active_by_group(
        self, group_id: int, as_of_date: date | None = None
    ) -> list[dict[str, Any]]:
        """Get active memberships by group"""
        if as_of_date is None:
            as_of_date = date.today()

        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT * FROM parliamentary_group_memberships
                    WHERE parliamentary_group_id = :group_id
                    AND start_date <= :as_of_date
                    AND (end_date IS NULL OR end_date >= :as_of_date)
                """),
                {"group_id": group_id, "as_of_date": as_of_date},
            )
            return [dict(row._mapping) for row in result]

    async def get_current_members(self, group_id: int) -> list[dict[str, Any]]:
        """Get current members of a parliamentary group"""
        return await self.get_active_by_group(group_id, date.today())

    async def create_membership(
        self,
        politician_id: int,
        group_id: int,
        start_date: date,
        role: str | None = None,
    ) -> dict[str, Any]:
        """Create a new membership in database"""
        with get_db_session() as session:
            # Check if already exists
            existing = session.execute(
                text("""
                    SELECT * FROM parliamentary_group_memberships
                    WHERE politician_id = :politician_id
                    AND parliamentary_group_id = :group_id
                    AND start_date = :start_date
                """),
                {
                    "politician_id": politician_id,
                    "group_id": group_id,
                    "start_date": start_date,
                },
            ).first()

            if existing:
                return dict(existing._mapping)

            # Create new membership
            result = session.execute(
                text("""
                    INSERT INTO parliamentary_group_memberships
                    (politician_id, parliamentary_group_id, start_date, role,
                     created_at, updated_at)
                    VALUES (:politician_id, :group_id, :start_date, :role,
                            NOW(), NOW())
                    RETURNING *
                """),
                {
                    "politician_id": politician_id,
                    "group_id": group_id,
                    "start_date": start_date,
                    "role": role,
                },
            )
            session.commit()

            membership = result.first()
            if membership:
                # Log for debugging
                print(
                    f"✓ Created membership in DB: "
                    f"politician_id={politician_id}, "
                    f"group_id={group_id}, role={role}"
                )
                return dict(membership._mapping)

            return {}

    async def end_membership(
        self, membership_id: int, end_date: date
    ) -> dict[str, Any] | None:
        """End a membership"""
        with get_db_session() as session:
            result = session.execute(
                text("""
                    UPDATE parliamentary_group_memberships
                    SET end_date = :end_date, updated_at = NOW()
                    WHERE id = :membership_id
                    RETURNING *
                """),
                {"membership_id": membership_id, "end_date": end_date},
            )
            session.commit()

            membership = result.first()
            return dict(membership._mapping) if membership else None

    async def delete_by_group(self, group_id: int) -> int:
        """Delete all memberships for a group"""
        with get_db_session() as session:
            result = session.execute(
                text("""
                    DELETE FROM parliamentary_group_memberships
                    WHERE parliamentary_group_id = :group_id
                """),
                {"group_id": group_id},
            )
            session.commit()
            return result.rowcount

    async def get_all(self) -> list[dict[str, Any]]:
        """Get all memberships"""
        with get_db_session() as session:
            result = session.execute(
                text(
                    "SELECT * FROM parliamentary_group_memberships "
                    "ORDER BY created_at DESC"
                )
            )
            return [dict(row._mapping) for row in result]
