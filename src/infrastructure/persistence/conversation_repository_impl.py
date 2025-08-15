"""Conversation repository implementation."""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError as SQLIntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.database.base_repository import BaseRepository as LegacyBaseRepository
from src.database.speaker_matching_service import SpeakerMatchingService
from src.domain.entities.conversation import Conversation
from src.domain.repositories.conversation_repository import ConversationRepository
from src.exceptions import IntegrityError, SaveError
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.minutes_divide_processor.models import SpeakerAndSpeechContent

logger = logging.getLogger(__name__)


class ConversationModel:
    """Conversation database model (dynamic)."""

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)


class ConversationRepositoryImpl(
    BaseRepositoryImpl[Conversation], ConversationRepository
):
    """Implementation of conversation repository using SQLAlchemy."""

    def __init__(
        self,
        session: AsyncSession | Session,
        model_class: type[Any] | None = None,
        speaker_matching_service: SpeakerMatchingService | None = None,
    ):
        """Initialize repository.

        Args:
            session: Database session (async or sync)
            model_class: Optional model class for compatibility
            speaker_matching_service: Optional speaker matching service
        """
        # Use dynamic model if no model class provided
        if model_class is None:
            model_class = ConversationModel

        # Handle both async and sync sessions
        if isinstance(session, AsyncSession):
            super().__init__(session, Conversation, model_class)
            self.sync_session = None
            self.async_session = session
        else:
            # For sync session, create a wrapper
            self.sync_session = session
            self.async_session = None
            self.session = session
            self.entity_class = Conversation
            self.model_class = model_class

        self.speaker_matching_service = speaker_matching_service
        self.legacy_repo = None

        # Initialize legacy repository if sync session is provided
        if self.sync_session:
            self.legacy_repo = LegacyBaseRepository(
                use_session=True, session=self.sync_session
            )

    async def get_by_minutes(self, minutes_id: int) -> list[Conversation]:
        """Get all conversations for a minutes record."""
        if self.async_session:
            query = text("""
                SELECT * FROM conversations
                WHERE minutes_id = :minutes_id
                ORDER BY sequence_number
            """)
            result = await self.async_session.execute(query, {"minutes_id": minutes_id})
            rows = result.fetchall()
            return [self._row_to_entity(row) for row in rows]
        else:
            # Sync implementation
            if not self.sync_session:
                return []
            query = text("""
                SELECT * FROM conversations
                WHERE minutes_id = :minutes_id
                ORDER BY sequence_number
            """)
            result = self.sync_session.execute(query, {"minutes_id": minutes_id})
            rows = result.fetchall()
            return [self._row_to_entity(row) for row in rows]

    async def get_by_speaker(
        self, speaker_id: int, limit: int | None = None
    ) -> list[Conversation]:
        """Get all conversations by a speaker."""
        if self.async_session:
            query = text("""
                SELECT * FROM conversations
                WHERE speaker_id = :speaker_id
                ORDER BY sequence_number
                LIMIT :limit
            """)
            params = {"speaker_id": speaker_id, "limit": limit or 999999}
            result = await self.async_session.execute(query, params)
            rows = result.fetchall()
            return [self._row_to_entity(row) for row in rows]
        else:
            # Sync implementation
            if not self.sync_session:
                return []
            query = text("""
                SELECT * FROM conversations
                WHERE speaker_id = :speaker_id
                ORDER BY sequence_number
                LIMIT :limit
            """)
            params = {"speaker_id": speaker_id, "limit": limit or 999999}
            result = self.sync_session.execute(query, params)
            rows = result.fetchall()
            return [self._row_to_entity(row) for row in rows]

    async def get_unlinked(self, limit: int | None = None) -> list[Conversation]:
        """Get conversations without speaker links."""
        if self.async_session:
            query = text("""
                SELECT * FROM conversations
                WHERE speaker_id IS NULL
                ORDER BY id
                LIMIT :limit
            """)
            params = {"limit": limit or 999999}
            result = await self.async_session.execute(query, params)
            rows = result.fetchall()
            return [self._row_to_entity(row) for row in rows]
        else:
            # Sync implementation
            if not self.sync_session:
                return []
            query = text("""
                SELECT * FROM conversations
                WHERE speaker_id IS NULL
                ORDER BY id
                LIMIT :limit
            """)
            params = {"limit": limit or 999999}
            result = self.sync_session.execute(query, params)
            rows = result.fetchall()
            return [self._row_to_entity(row) for row in rows]

    async def bulk_create(
        self, conversations: list[Conversation]
    ) -> list[Conversation]:
        """Create multiple conversations at once."""
        if not conversations:
            return []

        if self.async_session:
            # Async bulk insert
            values = [
                {
                    "minutes_id": conv.minutes_id,
                    "speaker_id": conv.speaker_id,
                    "speaker_name": conv.speaker_name,
                    "comment": conv.comment,
                    "sequence_number": conv.sequence_number,
                    "chapter_number": conv.chapter_number,
                    "sub_chapter_number": conv.sub_chapter_number,
                }
                for conv in conversations
            ]

            query = text("""
                INSERT INTO conversations
                (minutes_id, speaker_id, speaker_name, comment, sequence_number,
                 chapter_number, sub_chapter_number)
                VALUES
                (:minutes_id, :speaker_id, :speaker_name, :comment, :sequence_number,
                 :chapter_number, :sub_chapter_number)
                RETURNING id
            """)

            created = []
            for value in values:
                result = await self.async_session.execute(query, value)
                conv_id = result.scalar()
                # Create new conversation with ID
                conv = Conversation(
                    id=conv_id,
                    comment=value["comment"],
                    sequence_number=value["sequence_number"],
                    minutes_id=value["minutes_id"],
                    speaker_id=value["speaker_id"],
                    speaker_name=value["speaker_name"],
                    chapter_number=value["chapter_number"],
                    sub_chapter_number=value["sub_chapter_number"],
                )
                created.append(conv)

            await self.async_session.commit()
            return created
        else:
            # Sync implementation
            if not self.legacy_repo:
                return []
            created = []
            for conv in conversations:
                conv_id = self.legacy_repo.insert(
                    table="conversations",
                    data={
                        "minutes_id": conv.minutes_id,
                        "speaker_id": conv.speaker_id,
                        "speaker_name": conv.speaker_name,
                        "comment": conv.comment,
                        "sequence_number": conv.sequence_number,
                        "chapter_number": conv.chapter_number,
                        "sub_chapter_number": conv.sub_chapter_number,
                    },
                    returning="id",
                )
                conv.id = conv_id
                created.append(conv)

            if self.sync_session:
                self.sync_session.commit()
            return created

    async def save_speaker_and_speech_content_list(
        self, speaker_and_speech_content_list: list[Any], minutes_id: int | None = None
    ) -> list[int]:
        """Save speaker and speech content list."""
        if not speaker_and_speech_content_list:
            logger.warning("No conversations to save")
            if self.async_session:
                await self.async_session.commit()
            elif self.sync_session:
                self.sync_session.commit()
            return []

        saved_ids: list[int] = []
        failed_count = 0

        try:
            for i, speaker_and_speech_content in enumerate(
                speaker_and_speech_content_list
            ):
                try:
                    conversation_id = await self._save_conversation(
                        speaker_and_speech_content, minutes_id
                    )
                    if conversation_id:
                        saved_ids.append(conversation_id)
                except Exception as e:
                    logger.warning(f"Failed to save conversation {i + 1}: {e}")
                    failed_count += 1

            if self.async_session:
                await self.async_session.commit()
            elif self.sync_session:
                self.sync_session.commit()

            if saved_ids:
                print(f"✅ {len(saved_ids)}件の発言データをデータベースに保存しました")
                logger.info(f"Saved {len(saved_ids)} conversations successfully")

            if failed_count > 0:
                logger.warning(f"Failed to save {failed_count} conversations")
                if failed_count == len(speaker_and_speech_content_list):
                    raise SaveError(
                        f"Failed to save all {failed_count} conversations",
                        {"failed_count": failed_count},
                    )

            return saved_ids

        except SQLIntegrityError as e:
            if self.async_session:
                await self.async_session.rollback()
            elif self.sync_session:
                self.sync_session.rollback()
            logger.error(f"Integrity error while saving conversations: {e}")
            raise IntegrityError(
                "Data integrity constraint violated while saving conversations",
                {"saved_count": len(saved_ids), "error": str(e)},
            ) from e
        except SQLAlchemyError as e:
            if self.async_session:
                await self.async_session.rollback()
            elif self.sync_session:
                self.sync_session.rollback()
            logger.error(f"Database error while saving conversations: {e}")
            raise SaveError(
                "Failed to save conversations to database",
                {
                    "saved_count": len(saved_ids),
                    "total_count": len(speaker_and_speech_content_list),
                    "error": str(e),
                },
            ) from e
        except Exception as e:
            if self.async_session:
                await self.async_session.rollback()
            elif self.sync_session:
                self.sync_session.rollback()
            logger.error(f"Unexpected error while saving conversations: {e}")
            raise SaveError(
                "Unexpected error occurred while saving conversations",
                {"saved_count": len(saved_ids), "error": str(e)},
            ) from e
        finally:
            if self.async_session:
                await self.async_session.close()
            elif self.sync_session:
                self.sync_session.close()

    async def _save_conversation(
        self,
        speaker_and_speech_content: SpeakerAndSpeechContent,
        minutes_id: int | None = None,
    ) -> int | None:
        """Save individual conversation."""
        # Find speaker_id
        speaker_id = await self._find_speaker_id(speaker_and_speech_content.speaker)

        # Insert new record
        if self.async_session:
            query = text("""
                INSERT INTO conversations
                (minutes_id, speaker_id, speaker_name, comment, sequence_number,
                 chapter_number, sub_chapter_number)
                VALUES
                (:minutes_id, :speaker_id, :speaker_name, :comment, :sequence_number,
                 :chapter_number, :sub_chapter_number)
                RETURNING id
            """)
            result = await self.async_session.execute(
                query,
                {
                    "minutes_id": minutes_id,
                    "speaker_id": speaker_id,
                    "speaker_name": speaker_and_speech_content.speaker,
                    "comment": speaker_and_speech_content.speech_content,
                    "sequence_number": speaker_and_speech_content.speech_order,
                    "chapter_number": speaker_and_speech_content.chapter_number,
                    "sub_chapter_number": speaker_and_speech_content.sub_chapter_number,
                },
            )
            conversation_id = result.scalar()
        else:
            if not self.legacy_repo:
                return None
            conversation_id = self.legacy_repo.insert(
                table="conversations",
                data={
                    "minutes_id": minutes_id,
                    "speaker_id": speaker_id,
                    "speaker_name": speaker_and_speech_content.speaker,
                    "comment": speaker_and_speech_content.speech_content,
                    "sequence_number": speaker_and_speech_content.speech_order,
                    "chapter_number": speaker_and_speech_content.chapter_number,
                    "sub_chapter_number": speaker_and_speech_content.sub_chapter_number,
                },
                returning="id",
            )

        if speaker_id:
            print(
                f"➕ 新規追加: {speaker_and_speech_content.speaker} "
                f"(ID: {conversation_id}, Speaker ID: {speaker_id})"
            )
        else:
            print(
                f"➕ 新規追加: {speaker_and_speech_content.speaker} "
                f"(ID: {conversation_id}, Speaker ID: NULL)"
            )

        return conversation_id

    async def _find_speaker_id(self, speaker_name: str) -> int | None:
        """Find speaker ID by name."""
        if self.speaker_matching_service and hasattr(
            self.speaker_matching_service, "find_speaker_id"
        ):
            return self.speaker_matching_service.find_speaker_id(speaker_name)  # type: ignore

        # Fallback to legacy implementation
        if self.async_session:
            query = text("""
                SELECT id FROM speakers
                WHERE name = :name OR name LIKE :name_pattern
                LIMIT 1
            """)
            result = await self.async_session.execute(
                query,
                {"name": speaker_name, "name_pattern": f"%{speaker_name}%"},
            )
            row = result.fetchone()
            return row.id if row else None
        else:
            return self._legacy_find_speaker_id(speaker_name)

    def _legacy_find_speaker_id(self, speaker_name: str) -> int | None:
        """Legacy synchronous find speaker ID."""
        if not self.sync_session:
            return None

        query = text("""
            SELECT id FROM speakers
            WHERE name = :name OR name LIKE :name_pattern
            LIMIT 1
        """)
        result = self.sync_session.execute(
            query,
            {"name": speaker_name, "name_pattern": f"%{speaker_name}%"},
        )
        row = result.fetchone()
        return row.id if row else None

    async def get_conversations_count(self) -> int:
        """Get total count of conversations."""
        if self.async_session:
            query = text("SELECT COUNT(*) FROM conversations")
            result = await self.async_session.execute(query)
            return result.scalar() or 0
        else:
            if not self.sync_session:
                return 0
            query = text("SELECT COUNT(*) FROM conversations")
            result = self.sync_session.execute(query)
            return result.scalar() or 0

    async def get_speaker_linking_stats(self) -> dict[str, Any]:
        """Get statistics about speaker linking."""
        if self.async_session:
            # Total conversations
            total_query = text("SELECT COUNT(*) FROM conversations")
            total_result = await self.async_session.execute(total_query)
            total = total_result.scalar() or 0

            # Linked conversations
            linked_query = text(
                "SELECT COUNT(*) FROM conversations WHERE speaker_id IS NOT NULL"
            )
            linked_result = await self.async_session.execute(linked_query)
            linked = linked_result.scalar() or 0

            # Unlinked conversations
            unlinked = total - linked

            # Linking rate
            linking_rate = (linked / total * 100) if total > 0 else 0

            return {
                "total_conversations": total,
                "linked_conversations": linked,
                "unlinked_conversations": unlinked,
                "linking_rate": linking_rate,
            }
        else:
            # Sync implementation
            if not self.sync_session:
                return {
                    "total_conversations": 0,
                    "linked_conversations": 0,
                    "unlinked_conversations": 0,
                    "linking_rate": 0,
                }
            total_query = text("SELECT COUNT(*) FROM conversations")
            total_result = self.sync_session.execute(total_query)
            total = total_result.scalar() or 0

            linked_query = text(
                "SELECT COUNT(*) FROM conversations WHERE speaker_id IS NOT NULL"
            )
            linked_result = self.sync_session.execute(linked_query)
            linked = linked_result.scalar() or 0

            unlinked = total - linked
            linking_rate = (linked / total * 100) if total > 0 else 0

            return {
                "total_conversations": total,
                "linked_conversations": linked,
                "unlinked_conversations": unlinked,
                "linking_rate": linking_rate,
            }

    async def get_conversations_with_pagination(
        self,
        page: int = 1,
        page_size: int = 10,
        speaker_name: str | None = None,
        meeting_id: int | None = None,
        has_speaker_id: bool | None = None,
    ) -> dict[str, Any]:
        """Get conversations with pagination and filters."""
        # Build WHERE conditions
        conditions: list[str] = []
        params: dict[str, Any] = {"limit": page_size, "offset": (page - 1) * page_size}

        if speaker_name:
            conditions.append("c.speaker_name ILIKE :speaker_name")
            params["speaker_name"] = f"%{speaker_name}%"

        if meeting_id:
            conditions.append("m.id = :meeting_id")
            params["meeting_id"] = meeting_id

        if has_speaker_id is not None:
            if has_speaker_id:
                conditions.append("c.speaker_id IS NOT NULL")
            else:
                conditions.append("c.speaker_id IS NULL")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Count query
        count_query = text(f"""
            SELECT COUNT(*)
            FROM conversations c
            LEFT JOIN minutes mi ON c.minutes_id = mi.id
            LEFT JOIN meetings m ON mi.meeting_id = m.id
            WHERE {where_clause}
        """)

        # Data query
        data_query = text(f"""
            SELECT
                c.id,
                c.speaker_name,
                c.comment,
                c.sequence_number,
                c.chapter_number,
                c.sub_chapter_number,
                c.speaker_id,
                c.minutes_id,
                m.name as meeting_title,
                m.date as meeting_date,
                s.name as linked_speaker_name,
                s.type as speaker_type,
                s.political_party_name as speaker_party_name,
                gb.name as governing_body_name,
                gb.organization_type as governing_body_type,
                conf.name as conference_name,
                p.id as politician_id,
                p.name as politician_name,
                pp.name as politician_party_name,
                p.position as politician_position,
                CASE WHEN p.id IS NOT NULL THEN TRUE ELSE FALSE END
                    as speaker_is_politician
            FROM conversations c
            LEFT JOIN minutes mi ON c.minutes_id = mi.id
            LEFT JOIN meetings m ON mi.meeting_id = m.id
            LEFT JOIN speakers s ON c.speaker_id = s.id
            LEFT JOIN conferences conf ON m.conference_id = conf.id
            LEFT JOIN governing_bodies gb ON conf.governing_body_id = gb.id
            LEFT JOIN politicians p ON s.id = p.speaker_id
            LEFT JOIN political_parties pp ON p.political_party_id = pp.id
            WHERE {where_clause}
            ORDER BY c.id DESC
            LIMIT :limit OFFSET :offset
        """)

        if self.async_session:
            # Get total count
            count_result = await self.async_session.execute(count_query, params)
            total_count = count_result.scalar() or 0

            # Get data
            data_result = await self.async_session.execute(data_query, params)
            rows = data_result.fetchall()
        else:
            # Sync implementation
            if not self.sync_session:
                return {
                    "conversations": [],
                    "total_count": 0,
                    "total_pages": 0,
                    "current_page": page,
                    "page_size": page_size,
                }
            count_result = self.sync_session.execute(count_query, params)
            total_count = count_result.scalar() or 0

            data_result = self.sync_session.execute(data_query, params)
            rows = data_result.fetchall()

        # Format results
        conversations = []
        for row in rows:
            conversations.append(
                {
                    "id": row.id,
                    "speaker_name": row.speaker_name,
                    "comment": row.comment[:100] + "..."
                    if len(row.comment) > 100
                    else row.comment,
                    "sequence_number": row.sequence_number,
                    "chapter_number": row.chapter_number,
                    "sub_chapter_number": row.sub_chapter_number,
                    "speaker_id": row.speaker_id,
                    "minutes_id": row.minutes_id,
                    "meeting_title": row.meeting_title,
                    "meeting_date": row.meeting_date,
                    "linked_speaker_name": row.linked_speaker_name,
                    "speaker_type": row.speaker_type,
                    "speaker_party_name": row.speaker_party_name,
                    "governing_body_name": row.governing_body_name,
                    "governing_body_type": row.governing_body_type,
                    "conference_name": row.conference_name,
                    "politician_id": row.politician_id,
                    "politician_name": row.politician_name,
                    "politician_party_name": row.politician_party_name,
                    "politician_position": row.politician_position,
                    "speaker_is_politician": row.speaker_is_politician,
                }
            )

        total_pages = (total_count + page_size - 1) // page_size

        return {
            "conversations": conversations,
            "total_count": total_count,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
        }

    async def update_speaker_links(self) -> int:
        """Update speaker links for conversations."""
        if self.speaker_matching_service and hasattr(
            self.speaker_matching_service, "update_all_conversations"
        ):
            # Use speaker matching service if available
            return self.speaker_matching_service.update_all_conversations()  # type: ignore

        # Fallback to basic implementation
        update_query = text("""
            UPDATE conversations c
            SET speaker_id = s.id
            FROM speakers s
            WHERE c.speaker_id IS NULL
            AND (c.speaker_name = s.name OR c.speaker_name ILIKE '%' || s.name || '%')
        """)

        if self.async_session:
            result = await self.async_session.execute(update_query)
            await self.async_session.commit()
            return result.rowcount  # type: ignore
        else:
            if not self.sync_session:
                return 0
            result = self.sync_session.execute(update_query)
            self.sync_session.commit()
            return result.rowcount  # type: ignore

    def _row_to_entity(self, row: Any) -> Conversation:
        """Convert database row to domain entity."""
        return Conversation(
            id=row.id,
            comment=row.comment,
            sequence_number=row.sequence_number,
            minutes_id=row.minutes_id,
            speaker_id=row.speaker_id,
            speaker_name=row.speaker_name,
            chapter_number=row.chapter_number,
            sub_chapter_number=row.sub_chapter_number,
        )

    def _to_entity(self, model: Any) -> Conversation:
        """Convert database model to domain entity."""
        return Conversation(
            id=getattr(model, "id", None),
            comment=model.comment,
            sequence_number=model.sequence_number,
            minutes_id=getattr(model, "minutes_id", None),
            speaker_id=getattr(model, "speaker_id", None),
            speaker_name=getattr(model, "speaker_name", None),
            chapter_number=getattr(model, "chapter_number", None),
            sub_chapter_number=getattr(model, "sub_chapter_number", None),
        )

    def _to_model(self, entity: Conversation) -> Any:
        """Convert domain entity to database model."""
        return ConversationModel(
            comment=entity.comment,
            sequence_number=entity.sequence_number,
            minutes_id=entity.minutes_id,
            speaker_id=entity.speaker_id,
            speaker_name=entity.speaker_name,
            chapter_number=entity.chapter_number,
            sub_chapter_number=entity.sub_chapter_number,
        )

    def _update_model(self, model: Any, entity: Conversation) -> None:
        """Update model fields from entity."""
        model.comment = entity.comment
        model.sequence_number = entity.sequence_number
        model.minutes_id = entity.minutes_id
        model.speaker_id = entity.speaker_id
        model.speaker_name = entity.speaker_name
        model.chapter_number = entity.chapter_number
        model.sub_chapter_number = entity.sub_chapter_number
