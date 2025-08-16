"""Speaker repository implementation."""

from typing import Any

from sqlalchemy import and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.application.dtos.speaker_dto import SpeakerWithConversationCountDTO
from src.domain.entities.speaker import Speaker
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class SpeakerRepositoryImpl(BaseRepositoryImpl[Speaker], SpeakerRepository):
    """Implementation of speaker repository using SQLAlchemy."""

    def __init__(self, session: AsyncSession, model_class: type[Any]):
        super().__init__(session, Speaker, model_class)

    async def get_by_name_party_position(
        self,
        name: str,
        political_party_name: str | None = None,
        position: str | None = None,
    ) -> Speaker | None:
        """Get speaker by name, party, and position."""
        conditions = [self.model_class.name == name]

        if political_party_name is not None:
            conditions.append(
                self.model_class.political_party_name == political_party_name
            )
        if position is not None:
            conditions.append(self.model_class.position == position)

        query = select(self.model_class).where(and_(*conditions))
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        if model:
            return self._to_entity(model)
        return None

    async def get_politicians(self) -> list[Speaker]:
        """Get all speakers who are politicians."""
        query = select(self.model_class).where(self.model_class.is_politician)
        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def search_by_name(self, name_pattern: str) -> list[Speaker]:
        """Search speakers by name pattern."""
        query = select(self.model_class).where(
            self.model_class.name.ilike(f"%{name_pattern}%")
        )
        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def upsert(self, speaker: Speaker) -> Speaker:
        """Insert or update speaker (upsert)."""
        # Check if exists
        existing = await self.get_by_name_party_position(
            speaker.name,
            speaker.political_party_name,
            speaker.position,
        )

        if existing:
            # Update existing
            speaker.id = existing.id
            return await self.update(speaker)
        else:
            # Create new
            return await self.create(speaker)

    def _to_entity(self, model: Any) -> Speaker:
        """Convert database model to domain entity."""
        return Speaker(
            name=model.name,
            type=model.type,
            political_party_name=model.political_party_name,
            position=model.position,
            is_politician=model.is_politician,
            id=model.id,
        )

    def _to_model(self, entity: Speaker) -> Any:
        """Convert domain entity to database model."""
        return self.model_class(
            name=entity.name,
            type=entity.type,
            political_party_name=entity.political_party_name,
            position=entity.position,
            is_politician=entity.is_politician,
        )

    def _update_model(self, model: Any, entity: Speaker) -> None:
        """Update model fields from entity."""
        model.name = entity.name
        model.type = entity.type
        model.political_party_name = entity.political_party_name
        model.position = entity.position
        model.is_politician = entity.is_politician

    async def get_speakers_with_conversation_count(
        self,
        limit: int | None = None,
        offset: int | None = None,
        speaker_type: str | None = None,
        is_politician: bool | None = None,
    ) -> list[SpeakerWithConversationCountDTO]:
        """Get speakers with their conversation count."""
        # Build the WHERE clause conditions
        conditions = []
        params = {}

        if speaker_type is not None:
            conditions.append("s.type = :speaker_type")
            params["speaker_type"] = speaker_type

        if is_politician is not None:
            conditions.append("s.is_politician = :is_politician")
            params["is_politician"] = is_politician

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        # Build the pagination clause
        pagination_clause = ""
        if limit is not None:
            pagination_clause += " LIMIT :limit"
            params["limit"] = limit
        if offset is not None:
            pagination_clause += " OFFSET :offset"
            params["offset"] = offset

        # Execute the query
        query = text(f"""
            SELECT
                s.id,
                s.name,
                s.type,
                s.political_party_name,
                s.position,
                s.is_politician,
                COUNT(c.id) as conversation_count
            FROM speakers s
            LEFT JOIN conversations c ON s.id = c.speaker_id
            {where_clause}
            GROUP BY s.id, s.name, s.type, s.political_party_name,
                     s.position, s.is_politician
            ORDER BY s.name
            {pagination_clause}
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        # Convert rows to DTOs
        return [
            SpeakerWithConversationCountDTO(
                id=row.id,
                name=row.name,
                type=row.type,
                political_party_name=row.political_party_name,
                position=row.position,
                is_politician=row.is_politician,
                conversation_count=row.conversation_count,
            )
            for row in rows
        ]

    async def find_by_name(self, name: str) -> Speaker | None:
        """Find speaker by name."""
        query = select(self.model_class).where(self.model_class.name == name)
        result = await self.session.execute(query)
        model = result.scalar_one_or_none()

        if model:
            return self._to_entity(model)
        return None

    async def get_speakers_not_linked_to_politicians(self) -> list[Speaker]:
        """Get speakers who are not linked to politicians (is_politician=False)."""
        query = (
            select(self.model_class)
            .where(
                self.model_class.is_politician == False  # noqa: E712
            )
            .order_by(self.model_class.name)
        )
        result = await self.session.execute(query)
        models = result.scalars().all()

        return [self._to_entity(model) for model in models]

    async def get_speakers_with_politician_info(self) -> list[dict[str, Any]]:
        """Get speakers with linked politician information."""
        query = text("""
            SELECT
                s.id,
                s.name,
                s.type,
                s.political_party_name,
                s.position,
                s.is_politician,
                p.id as politician_id,
                p.name as politician_name,
                pp.name as party_name_from_politician,
                COUNT(c.id) as conversation_count
            FROM speakers s
            LEFT JOIN politicians p ON s.id = p.speaker_id
            LEFT JOIN political_parties pp ON p.political_party_id = pp.id
            LEFT JOIN conversations c ON s.id = c.speaker_id
            GROUP BY s.id, s.name, s.type, s.political_party_name,
                     s.position, s.is_politician, p.id, p.name, pp.name
            ORDER BY s.name
        """)

        result = await self.session.execute(query)
        rows = result.fetchall()

        return [
            {
                "id": row.id,
                "name": row.name,
                "type": row.type,
                "political_party_name": row.political_party_name,
                "position": row.position,
                "is_politician": row.is_politician,
                "politician_id": row.politician_id,
                "politician_name": row.politician_name,
                "party_name_from_politician": row.party_name_from_politician,
                "conversation_count": row.conversation_count,
            }
            for row in rows
        ]

    async def get_speaker_politician_stats(self) -> dict[str, int | float]:
        """Get statistics of speaker-politician linkage."""
        query = text("""
            WITH stats AS (
                SELECT
                    COUNT(*) as total_speakers,
                    COUNT(CASE WHEN is_politician = TRUE THEN 1 END)
                        as politician_speakers,
                    COUNT(CASE WHEN is_politician = FALSE THEN 1 END)
                        as non_politician_speakers
                FROM speakers
            ),
            linked_stats AS (
                SELECT
                    COUNT(DISTINCT s.id) as linked_speakers
                FROM speakers s
                INNER JOIN politicians p ON s.id = p.speaker_id
                WHERE s.is_politician = TRUE
            )
            SELECT
                stats.total_speakers,
                stats.politician_speakers,
                stats.non_politician_speakers,
                linked_stats.linked_speakers,
                (stats.politician_speakers - linked_stats.linked_speakers)
                    as unlinked_politician_speakers,
                CASE
                    WHEN stats.politician_speakers > 0
                    THEN ROUND(
                        CAST(linked_stats.linked_speakers AS NUMERIC) * 100.0 /
                        stats.politician_speakers, 1
                    )
                    ELSE 0
                END as link_rate
            FROM stats, linked_stats
        """)

        result = await self.session.execute(query)
        row = result.fetchone()

        if row:
            return {
                "total_speakers": row.total_speakers,
                "politician_speakers": row.politician_speakers,
                "non_politician_speakers": row.non_politician_speakers,
                "linked_speakers": row.linked_speakers,
                "unlinked_politician_speakers": row.unlinked_politician_speakers,
                "link_rate": float(row.link_rate),
            }
        else:
            return {
                "total_speakers": 0,
                "politician_speakers": 0,
                "non_politician_speakers": 0,
                "linked_speakers": 0,
                "unlinked_politician_speakers": 0,
                "link_rate": 0.0,
            }
