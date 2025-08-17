"""Repository for managing conferences

This is a legacy wrapper that delegates to the new ConferenceRepositoryImpl.
"""

import logging
from collections.abc import Coroutine
from types import TracebackType
from typing import Any, TypeVar

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.exceptions import (
    DatabaseError,
    DeleteError,
    SaveError,
    UpdateError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ConferenceRepository:
    """Legacy wrapper for conference repository that delegates to the new impl."""

    def __init__(self, session: Session | None = None):
        """Initialize repository with optional session.

        Args:
            session: Optional database session
        """
        if session:
            self.engine = None
            self.connection = session
        else:
            from src.config.database import get_db_engine

            self.engine = get_db_engine()
            self.connection = None

        # Initialize the new implementation - delay until session is set
        self._impl_initialized = False
        self._impl_session = session

    def _ensure_impl(self):
        """Ensure implementation is initialized with correct session"""
        if not self._impl_initialized:
            # Create async session for the implementation
            import asyncio

            # Get database URL and convert to async
            import os

            from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

            from src.infrastructure.persistence.conference_repository_impl import (
                ConferenceRepositoryImpl,
            )

            db_url = os.getenv(
                "DATABASE_URL",
                "postgresql://polibase_user:polibase_pass@localhost:5432/polibase_db",
            )

            # Convert sync URL to async URL
            if "postgresql://" in db_url:
                async_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
            else:
                async_url = db_url

            # Create async engine and session
            async_engine = create_async_engine(async_url)

            # Create session in a coroutine
            async def create_session():
                async with AsyncSession(async_engine) as session:
                    return session

            # Get the session (will be closed later)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._async_session = AsyncSession(async_engine)

            self._impl = ConferenceRepositoryImpl(session=self._async_session)
            self._impl_initialized = True

    def _run_async(self, coro: Coroutine[Any, Any, T]) -> T:  # type: ignore[misc]
        """Run async coroutine in sync context"""
        import asyncio

        self._ensure_impl()

        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop
            pass

        if loop and loop.is_running():
            # We're in an async context already
            import threading

            result_container = {}
            exception_container = {}

            def run_in_thread():
                new_loop = None
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result = new_loop.run_until_complete(coro)
                    result_container["result"] = result
                except Exception as e:
                    exception_container["exception"] = e
                finally:
                    if new_loop:
                        new_loop.close()

            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join()

            if "exception" in exception_container:
                raise exception_container["exception"]
            return result_container.get("result")
        else:
            # No running loop, create one
            return asyncio.run(coro)

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit"""
        if self.connection:
            try:
                if exc_type:
                    self.connection.rollback()
                else:
                    self.connection.commit()
            finally:
                if self.engine:
                    self.connection.close()

    def close(self):
        """Close database connection"""
        if self.connection and self.engine:
            self.connection.close()

    def get_all_conferences(self) -> list[dict[str, Any]]:
        """Get all conferences with governing body information."""
        if not self.connection:
            if self.engine is not None:
                self.connection = self.engine.connect()
            else:
                raise RuntimeError("No database connection or engine available")

        try:
            query = text("""
                SELECT
                    c.id,
                    c.name,
                    c.type,
                    c.governing_body_id,
                    c.members_introduction_url,
                    c.created_at,
                    c.updated_at,
                    gb.name as governing_body_name,
                    gb.type as governing_body_type
                FROM conferences c
                LEFT JOIN governing_bodies gb ON c.governing_body_id = gb.id
                ORDER BY gb.name, c.name
            """)

            result = self.connection.execute(query)
            rows = result.fetchall()

            return [dict(row) for row in rows]

        except SQLAlchemyError as e:
            logger.error(f"Database error getting all conferences: {e}")
            raise DatabaseError(
                "Failed to get all conferences", {"error": str(e)}
            ) from e

    def get_conference_by_id(self, conference_id: int) -> dict[str, Any] | None:
        """Get conference by ID with governing body information."""
        if not self.connection:
            if self.engine is not None:
                self.connection = self.engine.connect()
            else:
                raise RuntimeError("No database connection or engine available")

        try:
            query = text("""
                SELECT
                    c.id,
                    c.name,
                    c.type,
                    c.governing_body_id,
                    c.members_introduction_url,
                    c.created_at,
                    c.updated_at,
                    gb.name as governing_body_name,
                    gb.type as governing_body_type
                FROM conferences c
                LEFT JOIN governing_bodies gb ON c.governing_body_id = gb.id
                WHERE c.id = :conference_id
            """)

            result = self.connection.execute(query, {"conference_id": conference_id})
            row = result.fetchone()

            if row:
                return dict(row)
            return None

        except SQLAlchemyError as e:
            logger.error(f"Database error getting conference by ID: {e}")
            raise DatabaseError(
                f"Failed to get conference ID {conference_id}",
                {"conference_id": conference_id, "error": str(e)},
            ) from e

    def get_conferences_by_governing_body(
        self, governing_body_id: int
    ) -> list[dict[str, Any]]:
        """Get all conferences for a governing body."""
        conferences = self._run_async(
            self._impl.get_by_governing_body(governing_body_id)
        )

        # Convert entities to dict format expected by legacy code
        result: list[dict[str, Any]] = []
        if conferences:
            for conf in conferences:
                result.append(
                    {
                        "id": conf.id,
                        "name": conf.name,
                        "type": conf.type,
                        "governing_body_id": conf.governing_body_id,
                        "members_introduction_url": conf.members_introduction_url,
                    }
                )
        return result

    def create_conference(
        self,
        name: str,
        governing_body_id: int,
        type: str | None = None,
    ) -> int | None:
        """Create a new conference."""
        if not self.connection:
            if self.engine is not None:
                self.connection = self.engine.connect()
            else:
                raise RuntimeError("No database connection or engine available")

        try:
            # Check if conference already exists
            check_query = text("""
                SELECT id FROM conferences
                WHERE name = :name AND governing_body_id = :governing_body_id
            """)

            existing = self.connection.execute(
                check_query, {"name": name, "governing_body_id": governing_body_id}
            ).fetchone()

            if existing:
                logger.warning(f"Conference already exists: {name}")
                return None

            # Insert new conference
            insert_query = text("""
                INSERT INTO conferences
                    (name, type, governing_body_id, created_at, updated_at)
                VALUES
                    (:name, :type, :governing_body_id,
                     CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
            """)

            result = self.connection.execute(
                insert_query,
                {
                    "name": name,
                    "type": type,
                    "governing_body_id": governing_body_id,
                },
            )

            conference_id = result.scalar()
            self.connection.commit()

            logger.info(f"Created conference: {name} (ID: {conference_id})")
            return conference_id

        except SQLAlchemyError as e:
            self.connection.rollback()
            logger.error(f"Database error creating conference: {e}")
            raise SaveError(
                f"Failed to create conference: {name}", {"name": name, "error": str(e)}
            ) from e

    def update_conference(
        self,
        conference_id: int,
        name: str | None = None,
        type: str | None = None,
        governing_body_id: int | None = None,
        members_introduction_url: str | None = None,
    ) -> bool:
        """Update conference information."""
        if not self.connection:
            if self.engine is not None:
                self.connection = self.engine.connect()
            else:
                raise RuntimeError("No database connection or engine available")

        try:
            # Build dynamic update query
            update_parts: list[str] = []
            params: dict[str, Any] = {"conference_id": conference_id}

            if name is not None:
                update_parts.append("name = :name")
                params["name"] = name

            if type is not None:
                update_parts.append("type = :type")
                params["type"] = type

            if governing_body_id is not None:
                update_parts.append("governing_body_id = :governing_body_id")
                params["governing_body_id"] = governing_body_id

            if members_introduction_url is not None:
                update_parts.append(
                    "members_introduction_url = :members_introduction_url"
                )
                params["members_introduction_url"] = members_introduction_url

            if not update_parts:
                return True  # Nothing to update

            update_parts.append("updated_at = CURRENT_TIMESTAMP")

            query = text(f"""
                UPDATE conferences
                SET {", ".join(update_parts)}
                WHERE id = :conference_id
            """)

            result = self.connection.execute(query, params)
            self.connection.commit()

            # Check rowcount safely
            from sqlalchemy.engine import CursorResult

            if isinstance(result, CursorResult) and result.rowcount > 0:
                logger.info(f"Updated conference ID: {conference_id}")
                return True
            else:
                logger.warning(f"No conference found with ID: {conference_id}")
                return False

        except SQLAlchemyError as e:
            self.connection.rollback()
            logger.error(f"Database error updating conference: {e}")
            raise UpdateError(
                f"Failed to update conference ID {conference_id}",
                {"conference_id": conference_id, "error": str(e)},
            ) from e

    def update_conference_members_url(
        self, conference_id: int, members_introduction_url: str | None
    ) -> bool:
        """Update conference members introduction URL."""
        result = self._run_async(
            self._impl.update_members_url(conference_id, members_introduction_url)
        )
        return bool(result)

    def delete_conference(self, conference_id: int) -> bool:
        """Delete a conference."""
        if not self.connection:
            if self.engine is not None:
                self.connection = self.engine.connect()
            else:
                raise RuntimeError("No database connection or engine available")

        try:
            # Check for related meetings
            check_query = text("""
                SELECT COUNT(*) as count FROM meetings
                WHERE conference_id = :conference_id
            """)

            result = self.connection.execute(
                check_query, {"conference_id": conference_id}
            )
            count = result.scalar()

            if count is not None and count > 0:
                logger.warning(
                    f"Cannot delete conference {conference_id}: "
                    f"has {count} related meetings"
                )
                return False

            # Delete the conference
            delete_query = text("""
                DELETE FROM conferences WHERE id = :conference_id
            """)

            result = self.connection.execute(
                delete_query, {"conference_id": conference_id}
            )
            self.connection.commit()

            # Check rowcount safely
            from sqlalchemy.engine import CursorResult

            if isinstance(result, CursorResult) and result.rowcount > 0:
                logger.info(f"Deleted conference ID: {conference_id}")
                return True
            else:
                logger.warning(f"No conference found with ID: {conference_id}")
                return False

        except SQLAlchemyError as e:
            self.connection.rollback()
            logger.error(f"Database error deleting conference: {e}")
            raise DeleteError(
                f"Failed to delete conference ID {conference_id}",
                {"conference_id": conference_id, "error": str(e)},
            ) from e

    def get_governing_bodies(
        self,
    ) -> list[dict[str, Any]]:  # TODO: Create GoverningBodyDict type
        """Get all governing bodies."""
        if not self.connection:
            if self.engine is not None:
                self.connection = self.engine.connect()
            else:
                raise RuntimeError("No database connection or engine available")

        try:
            query = text("""
                SELECT id, name, type, created_at, updated_at
                FROM governing_bodies
                ORDER BY type, name
            """)

            result = self.connection.execute(query)
            rows = result.fetchall()

            return [dict(row) for row in rows]  # type: ignore[return-value]

        except SQLAlchemyError as e:
            logger.error(f"Database error getting governing bodies: {e}")
            raise DatabaseError(
                "Failed to get governing bodies", {"error": str(e)}
            ) from e
