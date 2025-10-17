"""Domain port for database session operations.

This module defines the ISessionAdapter interface as a domain port.
The domain layer defines this interface, and the infrastructure layer
provides concrete implementations following the Dependency Inversion Principle.
"""

from abc import ABC, abstractmethod
from typing import Any


class ISessionAdapter(ABC):
    """Abstract interface for database session operations.

    This is a domain port that defines the contract for session management.
    The infrastructure layer provides concrete implementations (adapters).

    This interface enables:
    - Dependency Inversion: Domain defines needs, infrastructure implements
    - Testability: Easy to create mock implementations for testing
    - Flexibility: Can swap implementations without changing domain code
    """

    @abstractmethod
    async def execute(
        self, statement: Any, params: dict[str, Any] | None = None
    ) -> Any:
        """Execute a database statement.

        Args:
            statement: Database statement to execute (implementation-specific)
            params: Optional parameters for the statement

        Returns:
            Result from the execution (implementation-specific)

        Note:
            The concrete return type depends on the implementation.
            For SQLAlchemy, this returns a Result object.
        """
        pass

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction.

        Persists all pending changes to the database.
        """
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the current transaction.

        Discards all pending changes.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the session.

        Releases database resources. The session should not be used
        after calling this method.
        """
        pass

    @abstractmethod
    def add(self, instance: Any) -> None:
        """Add an instance to the session.

        Args:
            instance: Entity instance to add to the session

        Note:
            The instance is not persisted until commit() is called.
        """
        pass

    @abstractmethod
    def add_all(self, instances: list[Any]) -> None:
        """Add multiple instances to the session.

        Args:
            instances: List of entity instances to add

        Note:
            The instances are not persisted until commit() is called.
        """
        pass

    @abstractmethod
    async def flush(self) -> None:
        """Flush pending changes to the database.

        Makes changes visible within the current transaction without
        committing. Useful for getting auto-generated IDs or enforcing
        constraints before commit.
        """
        pass

    @abstractmethod
    async def refresh(self, instance: Any) -> None:
        """Refresh an instance from the database.

        Args:
            instance: Entity instance to refresh

        Reloads the instance's state from the database, discarding
        any uncommitted changes to that instance.
        """
        pass
