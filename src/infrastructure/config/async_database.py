"""Async database configuration and session management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.config.settings import settings


class AsyncDatabase:
    """Async database manager."""

    def __init__(self):
        """Initialize async database engine and session maker."""
        # Convert sync database URL to async
        database_url = settings.get_database_url()
        # Replace postgresql:// with postgresql+asyncpg://
        if database_url.startswith("postgresql://"):
            async_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        else:
            async_url = database_url

        self.engine = create_async_engine(async_url, echo=False)
        self.async_session_maker = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession]:
        """Get an async database session.

        Yields:
            AsyncSession: Database session
        """
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    @asynccontextmanager
    async def get_session_autocommit(self) -> AsyncGenerator[AsyncSession]:
        """Get an async database session with autocommit behavior.

        Each operation commits immediately, useful for batch operations
        where individual failures shouldn't affect others.

        Yields:
            AsyncSession: Database session with autocommit
        """
        async with self.async_session_maker() as session:
            try:
                yield session
                # Don't auto-commit here, let caller manage
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# Global instance
async_db = AsyncDatabase()


# Convenience function for backward compatibility
@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession]:
    """Get an async database session.

    Yields:
        AsyncSession: Database session
    """
    async with async_db.get_session() as session:
        yield session
