"""
PostgreSQL データベース設定ファイル

Provides database connection and session management with proper error handling.
"""

import logging
import os
from collections.abc import Generator
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ..exceptions import ConnectionError, DatabaseError

load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# データベース接続設定
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://polibase_user:polibase_password@localhost:5432/polibase_db",
)

# Engine singleton
_engine: Engine | None = None


def get_db_engine() -> Engine:
    """PostgreSQLデータベースエンジンを取得

    Returns:
        Engine: SQLAlchemy engine instance

    Raises:
        ConnectionError: If database connection fails
    """
    global _engine

    if _engine is None:
        try:
            _engine = create_engine(
                DATABASE_URL,
                pool_pre_ping=True,  # Verify connections before use
                pool_size=5,
                max_overflow=10,
            )
            logger.info("Database engine created successfully")
        except SQLAlchemyError as e:
            raise ConnectionError(
                "Failed to create database engine",
                {"url": DATABASE_URL.split("@")[0] + "@***", "error": str(e)},
            )

    return _engine


def get_db_session() -> Session:
    """データベースセッションを取得

    Returns:
        Session: SQLAlchemy session instance

    Raises:
        ConnectionError: If database connection fails
    """
    try:
        engine = get_db_engine()
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionLocal()
    except SQLAlchemyError as e:
        raise ConnectionError("Failed to create database session", {"error": str(e)})


@contextmanager
def get_db_session_context() -> Generator[Session]:
    """Context manager for database sessions

    Yields:
        Session: Database session that auto-commits on success and rolls back on error

    Raises:
        DatabaseError: If database operation fails
    """
    session = get_db_session()
    try:
        yield session
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error occurred: {e}")
        raise DatabaseError("Database operation failed", {"error": str(e)})
    except Exception as e:
        session.rollback()
        logger.error(f"Unexpected error during database operation: {e}")
        raise
    finally:
        session.close()


def test_connection() -> bool:
    """データベース接続をテスト

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        engine = get_db_engine()
        with engine.connect() as connection:
            from sqlalchemy import text

            connection.execute(text("SELECT 1"))
            logger.info("PostgreSQL データベース接続成功")
            print("PostgreSQL データベース接続成功")
            return True
    except ConnectionError as e:
        logger.error(f"PostgreSQL データベース接続エラー: {e}")
        print(f"PostgreSQL データベース接続エラー: {e}")
        return False
    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
        print(f"PostgreSQL データベース接続エラー: {e}")
        return False


def close_db_engine() -> None:
    """Close the database engine and dispose of the connection pool"""
    global _engine

    if _engine is not None:
        _engine.dispose()
        _engine = None
        logger.info("Database engine closed")


if __name__ == "__main__":
    test_connection()
