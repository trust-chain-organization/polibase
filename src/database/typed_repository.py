"""Type-safe repository base class."""

import logging
from collections.abc import Sequence
from contextlib import contextmanager
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import Engine, Result, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.config.database import get_db_engine, get_db_session

logger = logging.getLogger(__name__)


class TypedRepository[T: PydanticBaseModel]:
    """Type-safe repository base class with common database operations."""

    def __init__(self, model_class: type[T], table_name: str, use_session: bool = True):
        """
        Initialize repository with model class and table name.

        Args:
            model_class: The Pydantic model class this repository handles
            table_name: Name of the database table
            use_session: If True, use SQLAlchemy session. If False, use engine directly.
        """
        self.model_class = model_class
        self.table_name = table_name
        self._use_session = use_session
        self._session: Session | None = None
        self._engine: Engine | None = None

        if use_session:
            self._session = get_db_session()
        else:
            self._engine = get_db_engine()

    @property
    def session(self) -> Session:
        """Get the current session."""
        if not self._session:
            raise RuntimeError("Repository is configured to use engine, not session")
        return self._session

    @property
    def engine(self) -> Engine:
        """Get the current engine."""
        if not self._engine:
            raise RuntimeError("Repository is configured to use session, not engine")
        return self._engine

    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
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

    def commit(self) -> None:
        """Commit the current transaction."""
        if self._use_session and self._session:
            self._session.commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        if self._use_session and self._session:
            self._session.rollback()

    def execute_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> Result[Any]:
        """Execute a query with parameters."""
        try:
            if self._use_session:
                return self.session.execute(text(query), params or {})
            else:
                with self.engine.connect() as conn:
                    return conn.execute(text(query), params or {})
        except SQLAlchemyError as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def fetch_one(self, query: str, params: dict[str, Any] | None = None) -> T | None:
        """Execute query and fetch one result as model."""
        result = self.execute_query(query, params)
        row = result.fetchone()
        if row:
            columns = result.keys()
            data = dict(zip(columns, row, strict=False))
            return self.model_class(**data)
        return None

    def fetch_all(
        self, query: str, params: dict[str, Any] | None = None
    ) -> Sequence[T]:
        """Execute query and fetch all results as models."""
        result = self.execute_query(query, params)
        models: list[T] = []
        for row in result.fetchall():
            columns = result.keys()
            data = dict(zip(columns, row, strict=False))
            models.append(self.model_class(**data))
        return models

    def get_by_id(self, id: int) -> T | None:
        """Get a single record by ID."""
        query = f"SELECT * FROM {self.table_name} WHERE id = :id"
        return self.fetch_one(query, {"id": id})

    def get_all(self) -> Sequence[T]:
        """Get all records."""
        query = f"SELECT * FROM {self.table_name} ORDER BY id"
        return self.fetch_all(query)

    def create_from_model(self, model: PydanticBaseModel) -> T:
        """Create a new record from a model and return it with ID."""
        data = model.model_dump(exclude_unset=True)
        # Remove id if it's None to let database generate it
        if "id" in data and data["id"] is None:
            del data["id"]

        columns = ", ".join(data.keys())
        values = ", ".join([f":{key}" for key in data.keys()])
        query = f"""
            INSERT INTO {self.table_name} ({columns})
            VALUES ({values})
            RETURNING *
        """

        with self.transaction():
            result = self.execute_query(query, data)
            row = result.fetchone()
            if row:
                columns = result.keys()
                data = dict(zip(columns, row, strict=False))
                return self.model_class(**data)
            raise RuntimeError("Failed to create record")

    def update_from_model(self, id: int, model: PydanticBaseModel) -> T | None:
        """Update a record by ID using a model."""
        data = model.model_dump(exclude_unset=True)
        # Remove id from update data
        if "id" in data:
            del data["id"]

        set_clause = ", ".join([f"{key} = :{key}" for key in data.keys()])
        query = f"""
            UPDATE {self.table_name}
            SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
            RETURNING *
        """

        params = data.copy()
        params["id"] = id

        with self.transaction():
            result = self.execute_query(query, params)
            row = result.fetchone()
            if row:
                columns = result.keys()
                data = dict(zip(columns, row, strict=False))
                return self.model_class(**data)
            return None

    def delete(self, id: int) -> bool:
        """Delete a record by ID."""
        query = f"DELETE FROM {self.table_name} WHERE id = :id"

        with self.transaction():
            self.execute_query(query, {"id": id})
            # For delete operations, if no exception was raised, it succeeded
            return True

    def exists(self, where: dict[str, Any]) -> bool:
        """Check if record exists."""
        where_clause = " AND ".join([f"{key} = :{key}" for key in where.keys()])
        query = f"SELECT 1 FROM {self.table_name} WHERE {where_clause} LIMIT 1"

        result = self.execute_query(query, where)
        return result.fetchone() is not None

    def count(self, where: dict[str, Any] | None = None) -> int:
        """Count records."""
        query = f"SELECT COUNT(*) FROM {self.table_name}"
        if where:
            where_clause = " AND ".join([f"{key} = :{key}" for key in where.keys()])
            query += f" WHERE {where_clause}"

        result = self.execute_query(query, where)
        row = result.fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        """Close database connection/session."""
        if self._session:
            self._session.close()
            self._session = None
        if self._engine:
            self._engine.dispose()
            self._engine = None

    def __enter__(self) -> "TypedRepository[T]":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - ensure resources are cleaned up."""
        self.close()
