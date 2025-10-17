"""Adapter to use sync Session with async repository."""

from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.engine.result import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session


class ISessionAdapter(ABC):
    """Abstract interface for session adapters.

    This interface defines the contract for session adapters that provide
    async-like operations for database sessions. Implementations can wrap
    sync sessions to provide async interfaces, enabling better testability
    and flexibility in repository implementations.
    """

    @abstractmethod
    async def execute(
        self, statement: Any, params: dict[str, Any] | None = None
    ) -> Result[Any]:
        """Execute a database statement.

        Args:
            statement: SQL statement to execute
            params: Optional parameters for the statement

        Returns:
            Result object from the execution
        """
        pass

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the session."""
        pass

    @abstractmethod
    def add(self, instance: Any) -> None:
        """Add an instance to the session.

        Args:
            instance: Database model instance to add
        """
        pass

    @abstractmethod
    def add_all(self, instances: list[Any]) -> None:
        """Add multiple instances to the session.

        Args:
            instances: List of database model instances to add
        """
        pass

    @abstractmethod
    async def flush(self) -> None:
        """Flush pending changes to the database."""
        pass

    @abstractmethod
    async def refresh(self, instance: Any) -> None:
        """Refresh an instance from the database.

        Args:
            instance: Database model instance to refresh
        """
        pass


# pyright: reportIncompatibleMethodOverride=false
class AsyncSessionAdapter(AsyncSession, ISessionAdapter):
    """Adapter that wraps sync Session to act like AsyncSession."""

    def __init__(self, sync_session: Session):
        """Initialize with a sync session."""
        self.sync_session = sync_session
        # Don't call super().__init__ as we're just wrapping

    async def execute(
        self, statement: Any, params: dict[str, Any] | None = None
    ) -> Result[Any]:
        """Execute a statement synchronously but return as if async."""
        if params:
            return self.sync_session.execute(statement, params)
        return self.sync_session.execute(statement)

    async def commit(self) -> None:
        """Commit synchronously but return as if async."""
        self.sync_session.commit()

    async def rollback(self) -> None:
        """Rollback synchronously but return as if async."""
        self.sync_session.rollback()

    async def close(self) -> None:
        """Close synchronously but return as if async."""
        self.sync_session.close()

    def add(self, instance: Any) -> None:
        """Add instance to session."""
        self.sync_session.add(instance)

    def add_all(self, instances: list[Any]) -> None:
        """Add multiple instances to session."""
        self.sync_session.add_all(instances)

    async def flush(self) -> None:
        """Flush synchronously but return as if async."""
        self.sync_session.flush()

    async def refresh(self, instance: Any) -> None:
        """Refresh instance synchronously but return as if async."""
        self.sync_session.refresh(instance)
