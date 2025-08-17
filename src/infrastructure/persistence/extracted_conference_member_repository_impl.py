"""ExtractedConferenceMember repository implementation using SQLAlchemy."""

from datetime import datetime

from sqlalchemy import and_, func, update
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.extracted_conference_member import ExtractedConferenceMember
from src.domain.repositories.extracted_conference_member_repository import (
    ExtractedConferenceMemberRepository as IExtractedConferenceMemberRepository,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.models.extracted_conference_member import (
    ExtractedConferenceMember as ExtractedConferenceMemberModel,
)


class ExtractedConferenceMemberRepositoryImpl(
    BaseRepositoryImpl[ExtractedConferenceMember], IExtractedConferenceMemberRepository
):
    """Implementation of ExtractedConferenceMemberRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        super().__init__(
            session, ExtractedConferenceMember, ExtractedConferenceMemberModel
        )

    async def get_pending_members(
        self, conference_id: int | None = None
    ) -> list[ExtractedConferenceMember]:
        """Get all pending members for matching."""
        query = select(ExtractedConferenceMemberModel).where(
            ExtractedConferenceMemberModel.matching_status == "pending"
        )

        if conference_id is not None:
            query = query.where(
                ExtractedConferenceMemberModel.conference_id == conference_id
            )

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_matched_members(
        self, conference_id: int | None = None, min_confidence: float | None = None
    ) -> list[ExtractedConferenceMember]:
        """Get matched members with optional filtering."""
        query = select(ExtractedConferenceMemberModel).where(
            ExtractedConferenceMemberModel.matching_status == "matched"
        )

        if conference_id is not None:
            query = query.where(
                ExtractedConferenceMemberModel.conference_id == conference_id
            )

        if min_confidence is not None:
            query = query.where(
                ExtractedConferenceMemberModel.matching_confidence >= min_confidence
            )

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def update_matching_result(
        self,
        member_id: int,
        politician_id: int | None,
        confidence: float | None,
        status: str,
    ) -> ExtractedConferenceMember | None:
        """Update the matching result for a member."""
        stmt = (
            update(ExtractedConferenceMemberModel)
            .where(ExtractedConferenceMemberModel.id == member_id)
            .values(
                matched_politician_id=politician_id,
                matching_confidence=confidence,
                matching_status=status,
                matched_at=datetime.now(),
            )
        )

        await self.session.execute(stmt)
        await self.session.commit()

        # Return updated entity
        return await self.get_by_id(member_id)

    async def get_by_conference(
        self, conference_id: int
    ) -> list[ExtractedConferenceMember]:
        """Get all extracted members for a conference."""
        query = select(ExtractedConferenceMemberModel).where(
            ExtractedConferenceMemberModel.conference_id == conference_id
        )

        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_extraction_summary(
        self, conference_id: int | None = None
    ) -> dict[str, int]:
        """Get summary statistics for extracted members."""
        base_query = select(
            ExtractedConferenceMemberModel.matching_status,
            func.count(ExtractedConferenceMemberModel.id).label("count"),
        )

        if conference_id is not None:
            base_query = base_query.where(
                ExtractedConferenceMemberModel.conference_id == conference_id
            )

        base_query = base_query.group_by(ExtractedConferenceMemberModel.matching_status)

        result = await self.session.execute(base_query)
        rows = result.all()

        summary = {
            "total": 0,
            "pending": 0,
            "matched": 0,
            "no_match": 0,
            "needs_review": 0,
        }

        for row in rows:
            status = row.matching_status
            count = row.count
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

        if hasattr(model, "additional_data"):
            model.additional_data = entity.additional_data
