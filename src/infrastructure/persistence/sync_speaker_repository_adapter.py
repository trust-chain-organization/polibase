"""Synchronous adapter for SpeakerRepository to support legacy code."""

import asyncio
from collections.abc import Coroutine
from typing import Any

from sqlalchemy.orm import Session

from src.domain.entities.speaker import Speaker
from src.infrastructure.persistence.async_session_adapter import AsyncSessionAdapter
from src.infrastructure.persistence.speaker_repository_impl import (
    SpeakerRepositoryImpl,
)
from src.models.speaker_v2 import Speaker as SpeakerModel


class SyncSpeakerRepositoryAdapter:
    """Synchronous adapter for async SpeakerRepository."""

    def __init__(self, session: Session | None = None):
        """Initialize synchronous adapter."""
        self.session = session
        self.model_class = SpeakerModel
        self.table_name = "speakers"

        # Create async adapter and repository implementation
        if self.session is not None:
            self.async_session = AsyncSessionAdapter(self.session)
            self.async_repo = SpeakerRepositoryImpl(self.async_session)
        else:
            self.async_session = None  # type: ignore[assignment]
            self.async_repo = None  # type: ignore[assignment]

        # Create or get event loop
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

    def _run_async(self, coro: Coroutine[Any, Any, Any]) -> Any:
        """Helper to run async code in sync context."""
        # If there's already a running loop, create a new thread
        try:
            # Try to use the existing loop
            if self.loop.is_running():
                # We're in an async context, can't use run_until_complete
                import threading

                result = None
                exception = None

                def run_in_thread():
                    nonlocal result, exception
                    try:
                        # Create new loop for thread
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        result = new_loop.run_until_complete(coro)
                    except Exception as e:
                        exception = e
                    finally:
                        new_loop.close()  # type: ignore[possibly-undefined]

                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()

                if exception:
                    raise exception
                return result
            else:
                return self.loop.run_until_complete(coro)
        except RuntimeError:
            # No loop or closed loop, create new one
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()

    def find_by_name(self, name: str) -> SpeakerModel | None:
        """Find speaker by name."""
        if not self.async_repo:
            return None
        result = self._run_async(self.async_repo.find_by_name(name))
        if result:
            return self._entity_to_model(result)
        return None

    def get_all_speakers(self) -> list[SpeakerModel]:
        """Get all speakers."""
        if not self.async_repo:
            return []
        entities = self._run_async(self.async_repo.get_all())
        return (
            [self._entity_to_model(entity) for entity in entities] if entities else []
        )

    def get_speakers_count(self) -> int:
        """Get count of speakers."""
        if not self.async_repo:
            return 0
        speakers = self._run_async(self.async_repo.get_all())
        return len(speakers) if speakers else 0

    def get_speakers_not_linked_to_politicians(self) -> list[SpeakerModel]:
        """Get speakers not linked to politicians."""
        if not self.async_repo:
            return []
        entities = self._run_async(
            self.async_repo.get_speakers_not_linked_to_politicians()
        )
        return (
            [self._entity_to_model(entity) for entity in entities] if entities else []
        )

    def get_speakers_with_politician_info(self) -> list[dict[str, Any]]:
        """Get speakers with politician info."""
        if not self.async_repo:
            return []
        result = self._run_async(self.async_repo.get_speakers_with_politician_info())
        return result if result else []

    def get_speaker_politician_stats(self) -> dict[str, int | float]:
        """Get speaker-politician statistics."""
        if not self.async_repo:
            return {
                "total_speakers": 0,
                "linked_to_politicians": 0,
                "link_percentage": 0.0,
            }
        result = self._run_async(self.async_repo.get_speaker_politician_stats())
        return (
            result
            if result
            else {
                "total_speakers": 0,
                "politician_speakers": 0,
                "non_politician_speakers": 0,
                "linked_speakers": 0,
                "unlinked_politician_speakers": 0,
                "link_rate": 0.0,
            }
        )

    def _entity_to_model(self, entity: Speaker) -> SpeakerModel:
        """Convert domain entity to database model."""
        model = SpeakerModel(
            name=entity.name,
            type=entity.type,
            political_party_name=entity.political_party_name,
            position=entity.position,
            is_politician=entity.is_politician,
        )
        if entity.id is not None:
            model.id = entity.id
        return model

    def _model_to_entity(self, model: SpeakerModel) -> Speaker:
        """Convert database model to domain entity."""
        return Speaker(
            id=model.id,
            name=model.name,
            type=model.type,
            political_party_name=model.political_party_name,
            position=model.position,
            is_politician=model.is_politician,
        )
