"""ExtractedConferenceMember repository implementation using SQLAlchemy."""

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.extracted_conference_member import ExtractedConferenceMember
from src.domain.repositories.extracted_conference_member_repository import (
    ExtractedConferenceMemberRepository as IExtractedConferenceMemberRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class ExtractedConferenceMemberModel:
    """Extracted conference member database model (dynamic)."""

    id: int | None
    conference_id: int
    extracted_name: str
    source_url: str
    extracted_role: str | None
    extracted_party_name: str | None
    extracted_at: datetime
    matched_politician_id: int | None
    matching_confidence: float | None
    matching_status: str
    matched_at: datetime | None
    additional_data: str | None

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)


class ExtractedConferenceMemberRepositoryImpl(
    BaseRepositoryImpl[ExtractedConferenceMember], IExtractedConferenceMemberRepository
):
    """Implementation of ExtractedConferenceMemberRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        super().__init__(
            session, ExtractedConferenceMember, ExtractedConferenceMemberModel
        )

    async def get_pending_members(
        self, conference_id: int | None = None
    ) -> list[ExtractedConferenceMember]:
        """Get all pending members for matching."""
        conditions = ["matching_status = 'pending'"]
        params: dict[str, Any] = {}

        if conference_id is not None:
            conditions.append("conference_id = :conf_id")
            params["conf_id"] = conference_id

        query = text(f"""
            SELECT * FROM extracted_conference_members
            WHERE {" AND ".join(conditions)}
            ORDER BY extracted_at DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_matched_members(
        self, conference_id: int | None = None, min_confidence: float | None = None
    ) -> list[ExtractedConferenceMember]:
        """Get matched members with optional filtering."""
        conditions = ["matching_status = 'matched'"]
        params: dict[str, Any] = {}

        if conference_id is not None:
            conditions.append("conference_id = :conf_id")
            params["conf_id"] = conference_id

        if min_confidence is not None:
            conditions.append("matching_confidence >= :min_conf")
            params["min_conf"] = min_confidence

        query = text(f"""
            SELECT * FROM extracted_conference_members
            WHERE {" AND ".join(conditions)}
            ORDER BY matching_confidence DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def update_matching_result(
        self,
        member_id: int,
        politician_id: int | None,
        confidence: float | None,
        status: str,
    ) -> ExtractedConferenceMember | None:
        """Update the matching result for a member."""
        query = text("""
            UPDATE extracted_conference_members
            SET matched_politician_id = :pol_id,
                matching_confidence = :confidence,
                matching_status = :status,
                matched_at = :matched_at
            WHERE id = :member_id
        """)

        await self.session.execute(
            query,
            {
                "member_id": member_id,
                "pol_id": politician_id,
                "confidence": confidence,
                "status": status,
                "matched_at": datetime.now(),
            },
        )
        await self.session.commit()

        # Return updated entity
        return await self.get_by_id(member_id)

    async def get_by_conference(
        self, conference_id: int
    ) -> list[ExtractedConferenceMember]:
        """Get all extracted members for a conference."""
        query = text("""
            SELECT * FROM extracted_conference_members
            WHERE conference_id = :conf_id
            ORDER BY extracted_name
        """)

        result = await self.session.execute(query, {"conf_id": conference_id})
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_extraction_summary(
        self, conference_id: int | None = None
    ) -> dict[str, int]:
        """Get summary statistics for extracted members."""
        where_clause = ""
        params: dict[str, Any] = {}

        if conference_id is not None:
            where_clause = "WHERE conference_id = :conf_id"
            params["conf_id"] = conference_id

        query = text(f"""
            SELECT matching_status, COUNT(*) as count
            FROM extracted_conference_members
            {where_clause}
            GROUP BY matching_status
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        summary = {
            "total": 0,
            "pending": 0,
            "matched": 0,
            "no_match": 0,
            "needs_review": 0,
        }

        for row in rows:
            status = row.matching_status
            count = getattr(row, "count", 0)  # Use getattr to access the count
            if status in summary:
                summary[status] = count
            summary["total"] += count

        return summary

    async def bulk_create(
        self, members: list[ExtractedConferenceMember]
    ) -> list[ExtractedConferenceMember]:
        """Create multiple extracted members at once."""
        models = [self._to_model(member) for member in members]
        self.session.add_all(models)
        await self.session.commit()

        # Refresh all models to get IDs
        for model in models:
            await self.session.refresh(model)

        return [self._to_entity(model) for model in models]

    def _row_to_entity(self, row: Any) -> ExtractedConferenceMember:
        """Convert database row to domain entity."""
        return ExtractedConferenceMember(
            id=row.id,
            conference_id=row.conference_id,
            extracted_name=row.extracted_name,
            source_url=row.source_url,
            extracted_role=getattr(row, "extracted_role", None),
            extracted_party_name=getattr(row, "extracted_party_name", None),
            extracted_at=row.extracted_at,
            matched_politician_id=getattr(row, "matched_politician_id", None),
            matching_confidence=getattr(row, "matching_confidence", None),
            matching_status=row.matching_status,
            matched_at=getattr(row, "matched_at", None),
            additional_data=getattr(row, "additional_data", None),
        )

    def _to_entity(
        self, model: ExtractedConferenceMemberModel
    ) -> ExtractedConferenceMember:
        """Convert database model to domain entity."""
        return ExtractedConferenceMember(
            id=model.id,
            conference_id=model.conference_id,
            extracted_name=model.extracted_name,
            source_url=model.source_url,
            extracted_role=model.extracted_role,
            extracted_party_name=model.extracted_party_name,
            extracted_at=model.extracted_at,
            matched_politician_id=model.matched_politician_id,
            matching_confidence=model.matching_confidence,
            matching_status=model.matching_status,
            matched_at=model.matched_at,
            additional_data=getattr(model, "additional_data", None),
        )

    def _to_model(
        self, entity: ExtractedConferenceMember
    ) -> ExtractedConferenceMemberModel:
        """Convert domain entity to database model."""
        data = {
            "conference_id": entity.conference_id,
            "extracted_name": entity.extracted_name,
            "source_url": entity.source_url,
            "extracted_role": entity.extracted_role,
            "extracted_party_name": entity.extracted_party_name,
            "extracted_at": entity.extracted_at,
            "matched_politician_id": entity.matched_politician_id,
            "matching_confidence": entity.matching_confidence,
            "matching_status": entity.matching_status,
            "matched_at": entity.matched_at,
        }

        if hasattr(entity, "additional_data") and entity.additional_data is not None:
            data["additional_data"] = entity.additional_data
        if entity.id is not None:
            data["id"] = entity.id

        return ExtractedConferenceMemberModel(**data)

    def _update_model(
        self,
        model: ExtractedConferenceMemberModel,
        entity: ExtractedConferenceMember,
    ) -> None:
        """Update model fields from entity."""
        model.conference_id = entity.conference_id
        model.extracted_name = entity.extracted_name
        model.source_url = entity.source_url
        model.extracted_role = entity.extracted_role
        model.extracted_party_name = entity.extracted_party_name
        model.extracted_at = entity.extracted_at
        model.matched_politician_id = entity.matched_politician_id
        model.matching_confidence = entity.matching_confidence
        model.matching_status = entity.matching_status
        model.matched_at = entity.matched_at

        if hasattr(entity, "additional_data") and entity.additional_data is not None:
            model.additional_data = entity.additional_data
