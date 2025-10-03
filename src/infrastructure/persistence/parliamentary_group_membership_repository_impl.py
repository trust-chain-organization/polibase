"""Parliamentary group membership repository implementation."""

from datetime import date
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.parliamentary_group_membership import (
    ParliamentaryGroupMembership as ParliamentaryGroupMembershipEntity,
)
from src.domain.repositories.parliamentary_group_membership_repository import (
    ParliamentaryGroupMembershipRepository,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.models.parliamentary_group import (
    ParliamentaryGroupMembership as ParliamentaryGroupMembershipModel,
)


class ParliamentaryGroupMembershipRepositoryImpl(
    BaseRepositoryImpl[ParliamentaryGroupMembershipEntity],
    ParliamentaryGroupMembershipRepository,
):
    """Parliamentary group membership repository implementation using SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: Async database session
        """
        super().__init__(
            session=session,
            entity_class=ParliamentaryGroupMembershipEntity,
            model_class=ParliamentaryGroupMembershipModel,
        )

    async def get_by_group(
        self, group_id: int
    ) -> list[ParliamentaryGroupMembershipEntity]:
        """Get memberships by group."""
        query = select(self.model_class).where(
            self.model_class.parliamentary_group_id == group_id
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def get_by_politician(
        self, politician_id: int
    ) -> list[ParliamentaryGroupMembershipEntity]:
        """Get memberships by politician."""
        query = select(self.model_class).where(
            self.model_class.politician_id == politician_id
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def get_active_by_group(
        self, group_id: int, as_of_date: date | None = None
    ) -> list[ParliamentaryGroupMembershipEntity]:
        """Get active memberships by group."""
        if as_of_date is None:
            as_of_date = date.today()

        query = select(self.model_class).where(
            and_(
                self.model_class.parliamentary_group_id == group_id,
                self.model_class.start_date <= as_of_date,
                (
                    self.model_class.end_date.is_(None)
                    | (self.model_class.end_date >= as_of_date)
                ),
            )
        )
        result = await self.session.execute(query)
        models = result.scalars().all()
        return [self._to_entity(model) for model in models]

    async def create_membership(
        self,
        politician_id: int,
        group_id: int,
        start_date: date,
        role: str | None = None,
    ) -> ParliamentaryGroupMembershipEntity:
        """Create a new membership."""
        # Check if already exists
        existing_query = select(self.model_class).where(
            and_(
                self.model_class.politician_id == politician_id,
                self.model_class.parliamentary_group_id == group_id,
                self.model_class.start_date == start_date,
            )
        )
        existing_result = await self.session.execute(existing_query)
        existing = existing_result.scalar_one_or_none()

        if existing:
            return self._to_entity(existing)

        # Create new membership
        entity = ParliamentaryGroupMembershipEntity(
            politician_id=politician_id,
            parliamentary_group_id=group_id,
            start_date=start_date,
            role=role,
        )

        model = self._to_model(entity)
        self.session.add(model)
        await (
            self.session.flush()
        )  # Use flush instead of commit for transaction control
        await self.session.refresh(model)

        return self._to_entity(model)

    async def end_membership(
        self, membership_id: int, end_date: date
    ) -> ParliamentaryGroupMembershipEntity | None:
        """End a membership."""
        model = await self.session.get(self.model_class, membership_id)
        if not model:
            return None

        model.end_date = end_date
        await self.session.flush()
        await self.session.refresh(model)

        return self._to_entity(model)

    async def get_current_members(self, group_id: int) -> list[dict[str, Any]]:
        """Get current members of a parliamentary group."""
        from sqlalchemy import text

        today = date.today()
        query = text("""
            SELECT
                id,
                politician_id,
                parliamentary_group_id,
                start_date,
                end_date,
                role
            FROM parliamentary_group_memberships
            WHERE parliamentary_group_id = :group_id
                AND start_date <= :today
                AND (end_date IS NULL OR end_date >= :today)
        """)

        result = await self.session.execute(
            query, {"group_id": group_id, "today": today}
        )
        rows = result.fetchall()

        return [
            {
                "id": row[0],
                "politician_id": row[1],
                "parliamentary_group_id": row[2],
                "start_date": row[3],
                "end_date": row[4],
                "role": row[5],
            }
            for row in rows
        ]

    def _to_entity(
        self, model: ParliamentaryGroupMembershipModel
    ) -> ParliamentaryGroupMembershipEntity:
        """Convert database model to domain entity."""
        return ParliamentaryGroupMembershipEntity(
            id=model.id,
            politician_id=model.politician_id,
            parliamentary_group_id=model.parliamentary_group_id,
            start_date=model.start_date,
            end_date=model.end_date,
            role=model.role,
        )

    def _to_model(
        self, entity: ParliamentaryGroupMembershipEntity
    ) -> ParliamentaryGroupMembershipModel:
        """Convert domain entity to database model."""
        from datetime import datetime

        return ParliamentaryGroupMembershipModel(
            id=entity.id or 0,  # Use 0 for new entities, will be set by DB
            politician_id=entity.politician_id,
            parliamentary_group_id=entity.parliamentary_group_id,
            start_date=entity.start_date,
            end_date=entity.end_date,
            role=entity.role,
            created_at=datetime.now() if not entity.id else None,
            updated_at=datetime.now(),
        )

    def _update_model(
        self,
        model: ParliamentaryGroupMembershipModel,
        entity: ParliamentaryGroupMembershipEntity,
    ) -> None:
        """Update model fields from entity."""
        model.politician_id = entity.politician_id
        model.parliamentary_group_id = entity.parliamentary_group_id
        model.start_date = entity.start_date
        model.end_date = entity.end_date
        model.role = entity.role
