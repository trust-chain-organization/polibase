"""Adapter to bridge sync legacy code with async new implementations."""

import asyncio
import logging
import types
from collections.abc import Awaitable
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
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
        self._async_session: AsyncSession | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def _get_or_create_event_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create an event loop for running async code."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No loop is running, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

    def _get_async_session(self) -> AsyncSession:
        """Get or create an async session."""
        if self._async_session is None:
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

            engine = create_async_engine(async_db_url, echo=False)
            async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
            self._async_session = async_session_maker()
        return self._async_session

    def _run_async(self, coro: Awaitable[T]) -> T:
        """Run an async coroutine from sync context."""
        try:
            loop = self._get_or_create_event_loop()

            # If loop is already running (e.g., in Jupyter), use different approach
            if loop.is_running():
                # Create a new thread to run the async code
                import threading

                result = None
                exception = None

                def run_in_thread():
                    nonlocal result, exception
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result = new_loop.run_until_complete(coro)
                    except Exception as e:
                        logger.error(f"Error in async execution: {e}")
                        exception = e
                    finally:
                        new_loop.close()

                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()

                if exception:
                    raise exception
                return result  # type: ignore
            else:
                # Normal case: run in the current thread
                return loop.run_until_complete(coro)
        except Exception as e:
            logger.error(f"Failed to run async operation: {e}")
            raise

    def __getattr__(self, name: str) -> Any:
        """
        Proxy method calls to the async repository.

        This allows the adapter to be used as if it were the repository itself.
        """

        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            session = self._get_async_session()
            repo = self.async_repository_class(session)
            method = getattr(repo, name)
            return await method(*args, **kwargs)

        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return self._run_async(async_wrapper(*args, **kwargs))

        return sync_wrapper

    def close(self):
        """Close the async session if it exists."""
        if self._async_session:
            self._run_async(self._async_session.close())
            self._async_session = None

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
