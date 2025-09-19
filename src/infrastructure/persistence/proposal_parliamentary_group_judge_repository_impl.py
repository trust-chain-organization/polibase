"""ProposalParliamentaryGroupJudge repository implementation."""

from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proposal_parliamentary_group_judge import (
    ProposalParliamentaryGroupJudge,
)
from src.domain.repositories.proposal_parliamentary_group_judge_repository import (
    ProposalParliamentaryGroupJudgeRepository,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class ProposalParliamentaryGroupJudgeModel(PydanticBaseModel):
    """Proposal parliamentary group judge database model."""

    id: int | None = None
    proposal_id: int
    parliamentary_group_id: int
    judgment: str
    member_count: int | None = None
    note: str | None = None

    class Config:
        arbitrary_types_allowed = True


class ProposalParliamentaryGroupJudgeRepositoryImpl(
    BaseRepositoryImpl[ProposalParliamentaryGroupJudge],
    ProposalParliamentaryGroupJudgeRepository,
):
    """Implementation of ProposalParliamentaryGroupJudgeRepository."""

    def __init__(self, session: AsyncSession):
        super().__init__(
            session,
            ProposalParliamentaryGroupJudge,
            ProposalParliamentaryGroupJudgeModel,
        )

    async def get_by_id(self, entity_id: int) -> ProposalParliamentaryGroupJudge | None:
        """Get entity by ID."""
        query = text("""
            SELECT * FROM proposal_parliamentary_group_judges WHERE id = :id
        """)
        result = await self.session.execute(query, {"id": entity_id})
        row = result.fetchone()
        if row:
            return self._row_to_entity(row)
        return None

    async def create(
        self, entity: ProposalParliamentaryGroupJudge
    ) -> ProposalParliamentaryGroupJudge:
        """Create a new entity."""
        query = text("""
            INSERT INTO proposal_parliamentary_group_judges (
                proposal_id, parliamentary_group_id, judgment,
                member_count, note
            )
            VALUES (
                :proposal_id, :parliamentary_group_id, :judgment,
                :member_count, :note
            )
            RETURNING id, proposal_id, parliamentary_group_id, judgment,
                      member_count, note, created_at, updated_at
        """)

        params = {
            "proposal_id": entity.proposal_id,
            "parliamentary_group_id": entity.parliamentary_group_id,
            "judgment": entity.judgment,
            "member_count": entity.member_count,
            "note": entity.note,
        }

        result = await self.session.execute(query, params)
        row = result.fetchone()
        await self.session.commit()

        if row:
            return self._row_to_entity(row)
        raise RuntimeError("Failed to create proposal parliamentary group judge")

    async def get_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[ProposalParliamentaryGroupJudge]:
        """Get all entities with optional pagination."""
        query_str = "SELECT * FROM proposal_parliamentary_group_judges ORDER BY id"
        params: dict[str, Any] = {}

        if limit:
            query_str += " LIMIT :limit"
            params["limit"] = limit
        if offset:
            query_str += " OFFSET :offset"
            params["offset"] = offset

        query = text(query_str)
        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_by_proposal(
        self, proposal_id: int
    ) -> list[ProposalParliamentaryGroupJudge]:
        """Get all parliamentary group judges for a specific proposal."""
        query = text("""
            SELECT * FROM proposal_parliamentary_group_judges
            WHERE proposal_id = :proposal_id
            ORDER BY parliamentary_group_id
        """)

        result = await self.session.execute(query, {"proposal_id": proposal_id})
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_by_parliamentary_group(
        self, parliamentary_group_id: int
    ) -> list[ProposalParliamentaryGroupJudge]:
        """Get all proposal judges for a specific parliamentary group."""
        query = text("""
            SELECT * FROM proposal_parliamentary_group_judges
            WHERE parliamentary_group_id = :parliamentary_group_id
            ORDER BY proposal_id
        """)

        result = await self.session.execute(
            query, {"parliamentary_group_id": parliamentary_group_id}
        )
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_by_proposal_and_group(
        self, proposal_id: int, parliamentary_group_id: int
    ) -> ProposalParliamentaryGroupJudge | None:
        """Get judge for a specific proposal and parliamentary group."""
        query = text("""
            SELECT * FROM proposal_parliamentary_group_judges
            WHERE proposal_id = :proposal_id
              AND parliamentary_group_id = :parliamentary_group_id
        """)

        result = await self.session.execute(
            query,
            {
                "proposal_id": proposal_id,
                "parliamentary_group_id": parliamentary_group_id,
            },
        )
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def bulk_create(
        self, judges: list[ProposalParliamentaryGroupJudge]
    ) -> list[ProposalParliamentaryGroupJudge]:
        """Create multiple parliamentary group judges at once."""
        if not judges:
            return []

        # Build values for bulk insert
        values = []
        for judge in judges:
            values.append(
                {
                    "proposal_id": judge.proposal_id,
                    "parliamentary_group_id": judge.parliamentary_group_id,
                    "judgment": judge.judgment,
                    "member_count": judge.member_count,
                    "note": judge.note,
                }
            )

        # Create bulk insert query
        query = text("""
            INSERT INTO proposal_parliamentary_group_judges (
                proposal_id, parliamentary_group_id, judgment,
                member_count, note
            )
            VALUES (
                :proposal_id, :parliamentary_group_id, :judgment,
                :member_count, :note
            )
            RETURNING id, proposal_id, parliamentary_group_id, judgment,
                      member_count, note, created_at, updated_at
        """)

        created_judges = []
        for value in values:
            result = await self.session.execute(query, value)
            row = result.fetchone()
            if row:
                created_judges.append(self._row_to_entity(row))

        await self.session.commit()
        return created_judges

    def _row_to_entity(self, row: Any) -> ProposalParliamentaryGroupJudge:
        """Convert database row to domain entity."""
        return ProposalParliamentaryGroupJudge(
            id=row.id,
            proposal_id=row.proposal_id,
            parliamentary_group_id=row.parliamentary_group_id,
            judgment=row.judgment,
            member_count=getattr(row, "member_count", None),
            note=getattr(row, "note", None),
        )

    def _to_entity(
        self, model: ProposalParliamentaryGroupJudgeModel
    ) -> ProposalParliamentaryGroupJudge:
        """Convert database model to domain entity."""
        return ProposalParliamentaryGroupJudge(
            id=model.id,
            proposal_id=model.proposal_id,
            parliamentary_group_id=model.parliamentary_group_id,
            judgment=model.judgment,
            member_count=model.member_count,
            note=model.note,
        )

    def _to_model(
        self, entity: ProposalParliamentaryGroupJudge
    ) -> ProposalParliamentaryGroupJudgeModel:
        """Convert domain entity to database model."""
        return ProposalParliamentaryGroupJudgeModel(
            id=entity.id,
            proposal_id=entity.proposal_id,
            parliamentary_group_id=entity.parliamentary_group_id,
            judgment=entity.judgment,
            member_count=entity.member_count,
            note=entity.note,
        )

    def _update_model(
        self,
        model: ProposalParliamentaryGroupJudgeModel,
        entity: ProposalParliamentaryGroupJudge,
    ) -> None:
        """Update model fields from entity."""
        model.proposal_id = entity.proposal_id
        model.parliamentary_group_id = entity.parliamentary_group_id
        model.judgment = entity.judgment
        model.member_count = entity.member_count
        model.note = entity.note
