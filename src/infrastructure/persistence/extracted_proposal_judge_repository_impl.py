"""ExtractedProposalJudge repository implementation using SQLAlchemy."""

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge
from src.domain.entities.proposal_judge import ProposalJudge
from src.domain.repositories.extracted_proposal_judge_repository import (
    ExtractedProposalJudgeRepository as IExtractedProposalJudgeRepository,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class ExtractedProposalJudgeModel:
    """Extracted proposal judge database model (dynamic)."""

    id: int | None
    proposal_id: int
    extracted_politician_name: str | None
    extracted_party_name: str | None
    extracted_parliamentary_group_name: str | None
    extracted_judgment: str | None
    source_url: str | None
    extracted_at: datetime
    matched_politician_id: int | None
    matched_parliamentary_group_id: int | None
    matching_confidence: float | None
    matching_status: str
    matched_at: datetime | None
    additional_data: str | None

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)


class ExtractedProposalJudgeRepositoryImpl(
    BaseRepositoryImpl[ExtractedProposalJudge], IExtractedProposalJudgeRepository
):
    """Implementation of ExtractedProposalJudgeRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ExtractedProposalJudge, ExtractedProposalJudgeModel)

    async def get_pending_judges(
        self, proposal_id: int | None = None
    ) -> list[ExtractedProposalJudge]:
        """Get all pending judges for matching."""
        conditions = ["matching_status = 'pending'"]
        params: dict[str, Any] = {}

        if proposal_id is not None:
            conditions.append("proposal_id = :prop_id")
            params["prop_id"] = proposal_id

        query = text(f"""
            SELECT * FROM extracted_proposal_judges
            WHERE {" AND ".join(conditions)}
            ORDER BY extracted_at DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_matched_judges(
        self, proposal_id: int | None = None, min_confidence: float | None = None
    ) -> list[ExtractedProposalJudge]:
        """Get matched judges with optional filtering."""
        conditions = ["matching_status = 'matched'"]
        params: dict[str, Any] = {}

        if proposal_id is not None:
            conditions.append("proposal_id = :prop_id")
            params["prop_id"] = proposal_id

        if min_confidence is not None:
            conditions.append("matching_confidence >= :min_conf")
            params["min_conf"] = min_confidence

        query = text(f"""
            SELECT * FROM extracted_proposal_judges
            WHERE {" AND ".join(conditions)}
            ORDER BY matching_confidence DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_needs_review_judges(
        self, proposal_id: int | None = None
    ) -> list[ExtractedProposalJudge]:
        """Get judges that need manual review."""
        conditions = ["matching_status = 'needs_review'"]
        params: dict[str, Any] = {}

        if proposal_id is not None:
            conditions.append("proposal_id = :prop_id")
            params["prop_id"] = proposal_id

        query = text(f"""
            SELECT * FROM extracted_proposal_judges
            WHERE {" AND ".join(conditions)}
            ORDER BY extracted_at DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def update_matching_result(
        self,
        judge_id: int,
        politician_id: int | None = None,
        parliamentary_group_id: int | None = None,
        confidence: float | None = None,
        status: str = "pending",
    ) -> ExtractedProposalJudge | None:
        """Update the matching result for a judge."""
        query = text("""
            UPDATE extracted_proposal_judges
            SET matched_politician_id = :pol_id,
                matched_parliamentary_group_id = :group_id,
                matching_confidence = :confidence,
                matching_status = :status,
                matched_at = :matched_at
            WHERE id = :judge_id
        """)

        await self.session.execute(
            query,
            {
                "judge_id": judge_id,
                "pol_id": politician_id,
                "group_id": parliamentary_group_id,
                "confidence": confidence,
                "status": status,
                "matched_at": datetime.now(),
            },
        )
        await self.session.commit()

        # Return updated entity
        return await self.get_by_id(judge_id)

    async def get_by_proposal(self, proposal_id: int) -> list[ExtractedProposalJudge]:
        """Get all extracted judges for a proposal."""
        query = text("""
            SELECT * FROM extracted_proposal_judges
            WHERE proposal_id = :prop_id
            ORDER BY extracted_politician_name, extracted_parliamentary_group_name
        """)

        result = await self.session.execute(query, {"prop_id": proposal_id})
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_extraction_summary(
        self, proposal_id: int | None = None
    ) -> dict[str, int]:
        """Get summary statistics for extracted judges."""
        where_clause = ""
        params: dict[str, Any] = {}

        if proposal_id is not None:
            where_clause = "WHERE proposal_id = :prop_id"
            params["prop_id"] = proposal_id

        query = text(f"""
            SELECT matching_status, COUNT(*) as count
            FROM extracted_proposal_judges
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
        self, judges: list[ExtractedProposalJudge]
    ) -> list[ExtractedProposalJudge]:
        """Create multiple extracted judges at once."""
        models = [self._to_model(judge) for judge in judges]
        self.session.add_all(models)
        await self.session.commit()

        # Refresh all models to get IDs
        for model in models:
            await self.session.refresh(model)

        return [self._to_entity(model) for model in models]

    async def convert_to_proposal_judge(
        self, extracted_judge: ExtractedProposalJudge
    ) -> ProposalJudge:
        """Convert an extracted judge to a ProposalJudge entity."""
        if not extracted_judge.is_matched():
            raise ValueError(
                f"Cannot convert unmatched extracted judge "
                f"(status: {extracted_judge.matching_status})"
            )

        params = extracted_judge.convert_to_proposal_judge_params()
        return ProposalJudge(**params)

    async def bulk_convert_to_proposal_judges(
        self, proposal_id: int | None = None
    ) -> list[ProposalJudge]:
        """Convert all matched judges for a proposal to ProposalJudge entities."""
        matched_judges = await self.get_matched_judges(proposal_id=proposal_id)
        result = []

        for judge in matched_judges:
            try:
                proposal_judge = await self.convert_to_proposal_judge(judge)
                result.append(proposal_judge)
            except ValueError:
                # Skip judges that cannot be converted
                continue

        return result

    def _row_to_entity(self, row: Any) -> ExtractedProposalJudge:
        """Convert database row to domain entity."""
        return ExtractedProposalJudge(
            id=row.id,
            proposal_id=row.proposal_id,
            extracted_politician_name=getattr(row, "extracted_politician_name", None),
            extracted_party_name=getattr(row, "extracted_party_name", None),
            extracted_parliamentary_group_name=getattr(
                row, "extracted_parliamentary_group_name", None
            ),
            extracted_judgment=getattr(row, "extracted_judgment", None),
            source_url=getattr(row, "source_url", None),
            extracted_at=row.extracted_at,
            matched_politician_id=getattr(row, "matched_politician_id", None),
            matched_parliamentary_group_id=getattr(
                row, "matched_parliamentary_group_id", None
            ),
            matching_confidence=getattr(row, "matching_confidence", None),
            matching_status=row.matching_status,
            matched_at=getattr(row, "matched_at", None),
            additional_data=getattr(row, "additional_data", None),
        )

    def _to_entity(self, model: ExtractedProposalJudgeModel) -> ExtractedProposalJudge:
        """Convert database model to domain entity."""
        return ExtractedProposalJudge(
            id=model.id,
            proposal_id=model.proposal_id,
            extracted_politician_name=model.extracted_politician_name,
            extracted_party_name=model.extracted_party_name,
            extracted_parliamentary_group_name=model.extracted_parliamentary_group_name,
            extracted_judgment=model.extracted_judgment,
            source_url=model.source_url,
            extracted_at=model.extracted_at,
            matched_politician_id=model.matched_politician_id,
            matched_parliamentary_group_id=model.matched_parliamentary_group_id,
            matching_confidence=model.matching_confidence,
            matching_status=model.matching_status,
            matched_at=model.matched_at,
            additional_data=getattr(model, "additional_data", None),
        )

    def _to_model(self, entity: ExtractedProposalJudge) -> ExtractedProposalJudgeModel:
        """Convert domain entity to database model."""
        data = {
            "proposal_id": entity.proposal_id,
            "extracted_politician_name": entity.extracted_politician_name,
            "extracted_party_name": entity.extracted_party_name,
            "extracted_parliamentary_group_name": (
                entity.extracted_parliamentary_group_name
            ),
            "extracted_judgment": entity.extracted_judgment,
            "source_url": entity.source_url,
            "extracted_at": entity.extracted_at,
            "matched_politician_id": entity.matched_politician_id,
            "matched_parliamentary_group_id": entity.matched_parliamentary_group_id,
            "matching_confidence": entity.matching_confidence,
            "matching_status": entity.matching_status,
            "matched_at": entity.matched_at,
        }

        if hasattr(entity, "additional_data") and entity.additional_data is not None:
            data["additional_data"] = entity.additional_data
        if entity.id is not None:
            data["id"] = entity.id

        return ExtractedProposalJudgeModel(**data)

    def _update_model(
        self,
        model: ExtractedProposalJudgeModel,
        entity: ExtractedProposalJudge,
    ) -> None:
        """Update model fields from entity."""
        model.proposal_id = entity.proposal_id
        model.extracted_politician_name = entity.extracted_politician_name
        model.extracted_party_name = entity.extracted_party_name
        model.extracted_parliamentary_group_name = (
            entity.extracted_parliamentary_group_name
        )
        model.extracted_judgment = entity.extracted_judgment
        model.source_url = entity.source_url
        model.extracted_at = entity.extracted_at
        model.matched_politician_id = entity.matched_politician_id
        model.matched_parliamentary_group_id = entity.matched_parliamentary_group_id
        model.matching_confidence = entity.matching_confidence
        model.matching_status = entity.matching_status
        model.matched_at = entity.matched_at

        if hasattr(entity, "additional_data") and entity.additional_data is not None:
            model.additional_data = entity.additional_data

    async def get_pending_by_proposal(
        self, proposal_id: int
    ) -> list[ExtractedProposalJudge]:
        """Get pending judges for a specific proposal."""
        return await self.get_pending_judges(proposal_id)

    async def get_all_pending(self) -> list[ExtractedProposalJudge]:
        """Get all pending judges."""
        return await self.get_pending_judges()

    async def get_matched_by_proposal(
        self, proposal_id: int
    ) -> list[ExtractedProposalJudge]:
        """Get matched judges for a specific proposal."""
        return await self.get_matched_judges(proposal_id)

    async def get_all_matched(self) -> list[ExtractedProposalJudge]:
        """Get all matched judges."""
        return await self.get_matched_judges()

    async def mark_processed(self, judge_id: int) -> None:
        """Mark a judge as processed."""
        query = text("""
            UPDATE extracted_proposal_judges
            SET matching_status = 'processed',
                matched_at = CURRENT_TIMESTAMP
            WHERE id = :judge_id
        """)
        await self.session.execute(query, {"judge_id": judge_id})
