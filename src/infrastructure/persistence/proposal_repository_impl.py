"""Proposal repository implementation using SQLAlchemy."""

import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proposal import Proposal
from src.domain.repositories.proposal_repository import ProposalRepository
from src.exceptions import DatabaseError
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl

logger = logging.getLogger(__name__)


class ProposalModel(PydanticBaseModel):
    """Proposal database model."""

    id: int | None = None
    content: str
    status: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        arbitrary_types_allowed = True


class ProposalRepositoryImpl(BaseRepositoryImpl[Proposal], ProposalRepository):
    """Proposal repository implementation using SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        super().__init__(
            session=session,
            entity_class=Proposal,
            model_class=ProposalModel,
        )

    async def get_by_status(self, status: str) -> list[Proposal]:
        """Get proposals by status.

        Args:
            status: Status to filter by (e.g., "審議中", "可決", "否決")

        Returns:
            List of proposals with the specified status
        """
        try:
            query = text("""
                SELECT
                    id,
                    content,
                    status,
                    created_at,
                    updated_at
                FROM proposals
                WHERE status = :status
                ORDER BY created_at DESC
            """)

            result = await self.session.execute(query, {"status": status})
            rows = result.fetchall()

            results = []
            for row in rows:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                results.append(self._dict_to_entity(row_dict))
            return results

        except SQLAlchemyError as e:
            logger.error(f"Database error getting proposals by status: {e}")
            raise DatabaseError(
                "Failed to get proposals by status",
                {"status": status, "error": str(e)},
            ) from e

    async def get_all(
        self, limit: int | None = None, offset: int | None = 0
    ) -> list[Proposal]:
        """Get all proposals.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Proposal entities
        """
        try:
            query_text = """
                SELECT
                    id,
                    content,
                    status,
                    created_at,
                    updated_at
                FROM proposals
                ORDER BY created_at DESC
            """

            params: dict[str, int | None] = {}
            if limit is not None:
                query_text += " LIMIT :limit OFFSET :offset"
                params = {"limit": limit, "offset": offset or 0}

            result = await self.session.execute(text(query_text), params)
            rows = result.fetchall()

            results = []
            for row in rows:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                results.append(self._dict_to_entity(row_dict))
            return results

        except SQLAlchemyError as e:
            logger.error(f"Database error getting all proposals: {e}")
            raise DatabaseError("Failed to get all proposals", {"error": str(e)}) from e

    async def get_by_id(self, entity_id: int) -> Proposal | None:
        """Get proposal by ID.

        Args:
            entity_id: Proposal ID

        Returns:
            Proposal entity or None if not found
        """
        try:
            query = text("""
                SELECT
                    id,
                    content,
                    status,
                    created_at,
                    updated_at
                FROM proposals
                WHERE id = :id
            """)

            result = await self.session.execute(query, {"id": entity_id})
            row = result.fetchone()

            if row:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                return self._dict_to_entity(row_dict)
            return None

        except SQLAlchemyError as e:
            logger.error(f"Database error getting proposal by ID: {e}")
            raise DatabaseError(
                "Failed to get proposal by ID",
                {"id": entity_id, "error": str(e)},
            ) from e

    async def create(self, entity: Proposal) -> Proposal:
        """Create a new proposal.

        Args:
            entity: Proposal entity to create

        Returns:
            Created Proposal entity with ID
        """
        try:
            query = text("""
                INSERT INTO proposals (content, status)
                VALUES (:content, :status)
                RETURNING id, content, status, created_at, updated_at
            """)

            result = await self.session.execute(
                query,
                {
                    "content": entity.content,
                    "status": entity.status,
                },
            )
            row = result.fetchone()
            await self.session.commit()

            if row:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                return self._dict_to_entity(row_dict)

            raise DatabaseError("Failed to create proposal", {"entity": entity})

        except SQLAlchemyError as e:
            logger.error(f"Database error creating proposal: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to create proposal", {"entity": entity, "error": str(e)}
            ) from e

    async def update(self, entity: Proposal) -> Proposal:
        """Update an existing proposal.

        Args:
            entity: Proposal entity with updated values

        Returns:
            Updated Proposal entity
        """
        if not entity.id:
            raise ValueError("Entity must have an ID to update")

        try:
            query = text("""
                UPDATE proposals
                SET content = :content,
                    status = :status,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                RETURNING id, content, status, created_at, updated_at
            """)

            result = await self.session.execute(
                query,
                {
                    "id": entity.id,
                    "content": entity.content,
                    "status": entity.status,
                },
            )
            row = result.fetchone()
            await self.session.commit()

            if row:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                return self._dict_to_entity(row_dict)

            raise DatabaseError(
                f"Proposal with ID {entity.id} not found", {"entity": entity}
            )

        except SQLAlchemyError as e:
            logger.error(f"Database error updating proposal: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to update proposal", {"entity": entity, "error": str(e)}
            ) from e

    async def delete(self, entity_id: int) -> bool:
        """Delete a proposal by ID.

        Args:
            entity_id: Proposal ID to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            # Check if there are related records
            check_query = text("""
                SELECT COUNT(*) FROM proposal_judges WHERE proposal_id = :proposal_id
            """)
            result = await self.session.execute(check_query, {"proposal_id": entity_id})
            count = result.scalar()

            if count and count > 0:
                return False  # Cannot delete if there are related judges

            query = text("DELETE FROM proposals WHERE id = :id")
            result = await self.session.execute(query, {"id": entity_id})
            await self.session.commit()

            return result.rowcount > 0  # type: ignore[attr-defined]

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting proposal: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to delete proposal", {"id": entity_id, "error": str(e)}
            ) from e

    def _to_entity(self, model: ProposalModel) -> Proposal:
        """Convert database model to domain entity.

        Args:
            model: Database model

        Returns:
            Domain entity
        """
        return Proposal(
            id=model.id,
            content=model.content,
            status=model.status,
        )

    def _to_model(self, entity: Proposal) -> ProposalModel:
        """Convert domain entity to database model.

        Args:
            entity: Domain entity

        Returns:
            Database model
        """
        return ProposalModel(
            id=entity.id,
            content=entity.content,
            status=entity.status,
        )

    def _update_model(self, model: ProposalModel, entity: Proposal) -> None:
        """Update model from entity.

        Args:
            model: Database model to update
            entity: Source entity
        """
        model.content = entity.content
        model.status = entity.status

    def _dict_to_entity(self, data: dict[str, Any]) -> Proposal:
        """Convert dictionary to entity.

        Args:
            data: Dictionary with entity data

        Returns:
            Proposal entity
        """
        return Proposal(
            id=data.get("id"),
            content=data["content"],
            status=data.get("status"),
        )
