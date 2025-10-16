"""Adapter to use sync Session with async repository."""

from typing import Any

from sqlalchemy.engine.result import Result
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session


# pyright: reportIncompatibleMethodOverride=false
class AsyncSessionAdapter(AsyncSession):  # type: ignore[misc]
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
