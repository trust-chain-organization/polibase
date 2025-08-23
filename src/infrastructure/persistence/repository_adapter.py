"""Adapter to bridge sync legacy code with async new implementations."""

import asyncio
import logging
import types
from collections.abc import Awaitable
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from src.config.database import DATABASE_URL

T = TypeVar("T")
logger = logging.getLogger(__name__)


class RepositoryAdapter:
    """
    Adapter to use async repositories from sync code.

    This is a temporary bridge during migration from legacy repositories
    to new Clean Architecture implementations.
    """

    def __init__(
        self, async_repository_class: type, sync_session: Session | None = None
    ):
        """
        Initialize the adapter.

        Args:
            async_repository_class: The async repository class to adapt
            sync_session: Optional sync session (for context)
        """
        self.async_repository_class = async_repository_class
        self._async_engine = None
        self._async_session_factory = None

    def _get_async_session_factory(self):
        """Get or create an async session factory."""
        if self._async_session_factory is None:
            # Convert sync database URL to async
            db_url = DATABASE_URL
            if db_url.startswith("postgresql://"):
                async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
            elif db_url.startswith("postgresql+psycopg2://"):
                async_db_url = db_url.replace(
                    "postgresql+psycopg2://", "postgresql+asyncpg://"
                )
            else:
                async_db_url = db_url

            self._async_engine = create_async_engine(async_db_url, echo=False)
            self._async_session_factory = async_sessionmaker(
                self._async_engine, expire_on_commit=False
            )
        return self._async_session_factory

    def _run_async(self, coro: Awaitable[T]) -> T:
        """Run an async coroutine from sync context."""
        try:
            # Always use asyncio.run() for Streamlit compatibility
            # This ensures each call gets a fresh event loop
            return asyncio.run(coro)
        except Exception as e:
            logger.error(f"Failed to run async operation: {e}")
            raise

    def __getattr__(self, name: str) -> Any:
        """
        Proxy method calls to the async repository.

        This allows the adapter to be used as if it were the repository itself.
        """

        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create a new session for each call to avoid event loop issues
            session_factory = self._get_async_session_factory()
            async with session_factory() as session:
                repo = self.async_repository_class(session)
                method = getattr(repo, name)
                return await method(*args, **kwargs)

        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return self._run_async(async_wrapper(*args, **kwargs))

        return sync_wrapper

    def close(self):
        """Close the async engine if it exists."""
        if self._async_engine:
            asyncio.run(self._async_engine.dispose())
            self._async_engine = None
            self._async_session_factory = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.close()
