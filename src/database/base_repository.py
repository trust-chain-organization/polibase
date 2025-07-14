"""
Base repository class providing common database operations
"""

import logging
import types
from contextlib import contextmanager
from typing import Any, TypeVar

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.config.database import get_db_engine, get_db_session
from src.models.base import BaseModel, to_dict

# Type variable for generic repository pattern
T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository class with common database operations"""

    def __init__(self, use_session: bool = True):
        """
        Initialize repository with either session or engine

        Args:
            use_session: If True, use SQLAlchemy session. If False, use engine directly.
        """
        self._use_session = use_session
        self._session: Session | None = None
        self._engine: Engine | None = None

        if use_session:
            self._session = get_db_session()
        else:
            self._engine = get_db_engine()

    @property
    def session(self) -> Session:
        """Get the current session"""
        if not self._session:
            raise RuntimeError("Repository is configured to use engine, not session")
        return self._session

    @property
    def engine(self) -> Engine:
        """Get the current engine"""
        if not self._engine:
            raise RuntimeError("Repository is configured to use session, not engine")
        return self._engine

    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions

        Usage:
            with self.transaction():
                # perform database operations
                # automatically commits on success, rolls back on exception
        """
        if self._use_session:
            try:
                yield self.session
                self.session.commit()
            except Exception as e:
                self.session.rollback()
                logger.error(f"Transaction failed: {e}")
                raise
        else:
            with self.engine.begin() as conn:
                yield conn

    def commit(self):
        """Commit the current transaction (for backward compatibility)"""
        if self._use_session and self._session:
            self._session.commit()

    def rollback(self):
        """Rollback the current transaction (for backward compatibility)"""
        if self._use_session and self._session:
            self._session.rollback()

    def execute_query(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """
        Execute a query with parameters

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query result
        """
        try:
            if self._use_session:
                return self.session.execute(text(query), params or {})
            else:
                with self.engine.connect() as conn:
                    result = conn.execute(text(query), params or {})
                    conn.commit()
                    return result
        except SQLAlchemyError as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def fetch_one(self, query: str, params: dict[str, Any] | None = None) -> Any | None:
        """
        Execute query and fetch one result

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Single result row or None
        """
        result = self.execute_query(query, params)
        return result.fetchone()

    def fetch_all(self, query: str, params: dict[str, Any] | None = None) -> list[Any]:
        """
        Execute query and fetch all results

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of result rows
        """
        result = self.execute_query(query, params)
        return result.fetchall()

    def fetch_as_dict(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Execute query and return results as list of dictionaries

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of dictionaries with column names as keys
        """
        result = self.execute_query(query, params)
        columns = result.keys()
        return [dict(zip(columns, row, strict=False)) for row in result.fetchall()]

    def insert(
        self, table: str, data: dict[str, Any], returning: str | None = None
    ) -> Any | None:
        """
        Insert a record into table

        Args:
            table: Table name
            data: Dictionary of column names and values
            returning: Column name to return (usually 'id')

        Returns:
            Value of returning column if specified, None otherwise
        """
        columns = ", ".join(data.keys())
        values = ", ".join([f":{key}" for key in data.keys()])

        query = f"INSERT INTO {table} ({columns}) VALUES ({values})"
        if returning:
            query += f" RETURNING {returning}"

        with self.transaction():
            result = self.execute_query(query, data)
            if returning:
                return result.fetchone()[0]
        return None

    def update(self, table: str, data: dict[str, Any], where: dict[str, Any]) -> int:
        """
        Update records in table

        Args:
            table: Table name
            data: Dictionary of columns to update
            where: Dictionary of where conditions

        Returns:
            Number of affected rows
        """
        set_clause = ", ".join([f"{key} = :{key}" for key in data.keys()])
        where_clause = " AND ".join([f"{key} = :where_{key}" for key in where.keys()])

        query = (
            f"UPDATE {table} SET {set_clause}, "
            f"updated_at = CURRENT_TIMESTAMP WHERE {where_clause}"
        )

        # Prefix where parameters to avoid conflicts
        params = data.copy()
        params.update({f"where_{key}": value for key, value in where.items()})

        with self.transaction():
            result = self.execute_query(query, params)
            return result.rowcount

    def delete(self, table: str, where: dict[str, Any]) -> int:
        """
        Delete records from table

        Args:
            table: Table name
            where: Dictionary of where conditions

        Returns:
            Number of affected rows
        """
        where_clause = " AND ".join([f"{key} = :{key}" for key in where.keys()])
        query = f"DELETE FROM {table} WHERE {where_clause}"

        with self.transaction():
            result = self.execute_query(query, where)
            return result.rowcount

    def exists(self, table: str, where: dict[str, Any]) -> bool:
        """
        Check if record exists

        Args:
            table: Table name
            where: Dictionary of where conditions

        Returns:
            True if record exists, False otherwise
        """
        where_clause = " AND ".join([f"{key} = :{key}" for key in where.keys()])
        query = f"SELECT 1 FROM {table} WHERE {where_clause} LIMIT 1"

        result = self.fetch_one(query, where)
        return result is not None

    def count(self, table: str, where: dict[str, Any] | None = None) -> int:
        """
        Count records in table

        Args:
            table: Table name
            where: Optional dictionary of where conditions

        Returns:
            Number of records
        """
        query = f"SELECT COUNT(*) FROM {table}"
        if where:
            where_clause = " AND ".join([f"{key} = :{key}" for key in where.keys()])
            query += f" WHERE {where_clause}"

        result = self.fetch_one(query, where)
        return result[0] if result else 0

    def insert_model(
        self, table: str, model: BaseModel, returning: str | None = None
    ) -> Any | None:
        """
        Insert a Pydantic model into table

        Args:
            table: Table name
            model: Pydantic model instance
            returning: Column name to return (usually 'id')

        Returns:
            Value of returning column if specified, None otherwise
        """
        data = to_dict(model)
        return self.insert(table, data, returning)

    def update_model(self, table: str, model: BaseModel, where: dict[str, Any]) -> int:
        """
        Update records using a Pydantic model

        Args:
            table: Table name
            model: Pydantic model instance with values to update
            where: Dictionary of where conditions

        Returns:
            Number of affected rows
        """
        data = to_dict(model)
        return self.update(table, data, where)

    def fetch_as_model(
        self, model_class: type[T], query: str, params: dict[str, Any] | None = None
    ) -> T | None:
        """
        Execute query and return result as Pydantic model

        Args:
            model_class: Pydantic model class
            query: SQL query string
            params: Query parameters

        Returns:
            Model instance or None
        """
        result = self.fetch_one(query, params)
        if result:
            # Convert Row to dict
            columns = result._fields
            data = dict(zip(columns, result, strict=False))
            return model_class(**data)
        return None

    def fetch_all_as_models(
        self, model_class: type[T], query: str, params: dict[str, Any] | None = None
    ) -> list[T]:
        """
        Execute query and return results as list of Pydantic models

        Args:
            model_class: Pydantic model class
            query: SQL query string
            params: Query parameters

        Returns:
            List of model instances
        """
        results = self.fetch_all(query, params)
        models: list[T] = []
        for row in results:
            # Convert Row to dict
            columns = row._fields
            data = dict(zip(columns, row, strict=False))
            models.append(model_class(**data))
        return models

    def close(self):
        """Close database connection/session"""
        if self._session:
            self._session.close()
            self._session = None
        if self._engine:
            self._engine.dispose()
            self._engine = None

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Context manager exit - ensure resources are cleaned up"""
        self.close()
