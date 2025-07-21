"""Repository for managing governing bodies"""

import logging
import types
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError as SQLIntegrityError
from sqlalchemy.exc import SQLAlchemyError

from src.config.database import get_db_engine
from src.exceptions import (
    DatabaseError,
    DeleteError,
    IntegrityError,
    QueryError,
    SaveError,
    UpdateError,
)

logger = logging.getLogger(__name__)


class GoverningBodyRepository:
    """開催主体テーブルの操作を行うリポジトリクラス"""

    def __init__(self):
        self.engine = get_db_engine()
        self.connection = None

    def __enter__(self):
        self.connection = self.engine.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        if self.connection:
            self.connection.close()

    def close(self):
        """接続を閉じる"""
        if self.connection:
            self.connection.close()

    def get_all_governing_bodies(self) -> list[dict[str, Any]]:
        """すべての開催主体を取得

        Raises:
            QueryError: If database query fails
            ConnectionError: If database connection fails
        """
        try:
            if not self.connection:
                self.connection = self.engine.connect()

            query = text("""
                SELECT gb.id, gb.name, gb.type,
                       COUNT(DISTINCT c.id) as conference_count
                FROM governing_bodies gb
                LEFT JOIN conferences c ON gb.id = c.governing_body_id
                GROUP BY gb.id, gb.name, gb.type
                ORDER BY
                    CASE gb.type
                        WHEN '国' THEN 1
                        WHEN '都道府県' THEN 2
                        WHEN '市町村' THEN 3
                        ELSE 4
                    END,
                    gb.name
            """)

            result = self.connection.execute(query)
            governing_bodies: list[dict[str, Any]] = []
            for row in result:
                governing_bodies.append(
                    {
                        "id": row.id,
                        "name": row.name,
                        "type": row.type,
                        "conference_count": row.conference_count,
                    }
                )

            return governing_bodies
        except SQLAlchemyError as e:
            logger.error(f"Database error getting all governing bodies: {e}")
            raise QueryError(
                "Failed to retrieve governing bodies",
                {"error": str(e)},
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error getting all governing bodies: {e}")
            raise DatabaseError(
                "Unexpected error retrieving governing bodies",
                {"error": str(e)},
            ) from e

    def get_governing_body_by_id(self, governing_body_id: int) -> dict[str, Any] | None:
        """IDで開催主体を取得

        Raises:
            QueryError: If database query fails
        """
        try:
            if not self.connection:
                self.connection = self.engine.connect()

            query = text("""
                SELECT id, name, type
                FROM governing_bodies
                WHERE id = :governing_body_id
            """)

            result = self.connection.execute(
                query, {"governing_body_id": governing_body_id}
            )
            row = result.fetchone()

            if row:
                return {"id": row.id, "name": row.name, "type": row.type}

            return None
        except SQLAlchemyError as e:
            logger.error(
                f"Database error getting governing body {governing_body_id}: {e}"
            )
            raise QueryError(
                f"Failed to retrieve governing body with ID {governing_body_id}",
                {"governing_body_id": governing_body_id, "error": str(e)},
            ) from e

    def get_governing_bodies_by_type(self, gb_type: str) -> list[dict[str, Any]]:
        """種別で開催主体を取得

        Raises:
            QueryError: If database query fails
        """
        try:
            if not self.connection:
                self.connection = self.engine.connect()

            query = text("""
                SELECT gb.id, gb.name, gb.type,
                       COUNT(DISTINCT c.id) as conference_count
                FROM governing_bodies gb
                LEFT JOIN conferences c ON gb.id = c.governing_body_id
                WHERE gb.type = :type
                GROUP BY gb.id, gb.name, gb.type
                ORDER BY gb.name
            """)

            result = self.connection.execute(query, {"type": gb_type})
            governing_bodies: list[dict[str, Any]] = []
            for row in result:
                governing_bodies.append(
                    {
                        "id": row.id,
                        "name": row.name,
                        "type": row.type,
                        "conference_count": row.conference_count,
                    }
                )

            return governing_bodies
        except SQLAlchemyError as e:
            logger.error(
                f"Database error getting governing bodies by type '{gb_type}': {e}"
            )
            raise QueryError(
                f"Failed to retrieve governing bodies of type '{gb_type}'",
                {"type": gb_type, "error": str(e)},
            ) from e

    def create_governing_body(self, name: str, gb_type: str) -> int | None:
        """新しい開催主体を作成"""
        if not self.connection:
            self.connection = self.engine.connect()

        try:
            # 既存チェック
            check_query = text("""
                SELECT id FROM governing_bodies
                WHERE name = :name AND type = :type
            """)
            existing = self.connection.execute(
                check_query, {"name": name, "type": gb_type}
            ).fetchone()

            if existing:
                logger.warning(f"Governing body already exists: {name} ({gb_type})")
                return None

            query = text("""
                INSERT INTO governing_bodies (name, type)
                VALUES (:name, :type)
                RETURNING id
            """)

            result = self.connection.execute(query, {"name": name, "type": gb_type})

            self.connection.commit()
            row = result.fetchone()
            if row is None:
                logger.error("Failed to get governing body ID after creation")
                return None
            governing_body_id = row[0]
            logger.info(f"Created governing body with ID: {governing_body_id}")
            return governing_body_id

        except SQLIntegrityError as e:
            self.connection.rollback()
            logger.error(f"Integrity error creating governing body: {e}")
            raise IntegrityError(
                f"Governing body '{name}' of type '{gb_type}' may already exist",
                {"name": name, "type": gb_type, "error": str(e)},
            ) from e
        except SQLAlchemyError as e:
            self.connection.rollback()
            logger.error(f"Database error creating governing body: {e}")
            raise SaveError(
                f"Failed to create governing body '{name}'",
                {"name": name, "type": gb_type, "error": str(e)},
            ) from e
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Unexpected error creating governing body: {e}")
            raise SaveError(
                f"Unexpected error creating governing body '{name}'",
                {"name": name, "type": gb_type, "error": str(e)},
            ) from e

    def update_governing_body(
        self, governing_body_id: int, name: str, gb_type: str
    ) -> bool:
        """開催主体を更新"""
        if not self.connection:
            self.connection = self.engine.connect()

        try:
            # 既存チェック（自分以外）
            check_query = text("""
                SELECT id FROM governing_bodies
                WHERE name = :name AND type = :type AND id != :id
            """)
            existing = self.connection.execute(
                check_query, {"name": name, "type": gb_type, "id": governing_body_id}
            ).fetchone()

            if existing:
                logger.warning(
                    f"Another governing body with same name and type exists: {name} ({gb_type})"
                )
                return False

            query = text("""
                UPDATE governing_bodies
                SET name = :name, type = :type, updated_at = CURRENT_TIMESTAMP
                WHERE id = :governing_body_id
            """)

            self.connection.execute(
                query,
                {"governing_body_id": governing_body_id, "name": name, "type": gb_type},
            )

            self.connection.commit()
            logger.info(f"Updated governing body ID: {governing_body_id}")
            return True

        except SQLAlchemyError as e:
            self.connection.rollback()
            logger.error(f"Database error updating governing body: {e}")
            raise UpdateError(
                f"Failed to update governing body with ID {governing_body_id}",
                {"governing_body_id": governing_body_id, "error": str(e)},
            ) from e
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Unexpected error updating governing body: {e}")
            raise UpdateError(
                f"Unexpected error updating governing body with ID {governing_body_id}",
                {"governing_body_id": governing_body_id, "error": str(e)},
            ) from e

    def delete_governing_body(self, governing_body_id: int) -> bool:
        """開催主体を削除"""
        if not self.connection:
            self.connection = self.engine.connect()

        try:
            # まず、この開催主体に関連する会議体があるかチェック
            check_query = text("""
                SELECT COUNT(*) as count
                FROM conferences
                WHERE governing_body_id = :governing_body_id
            """)

            result = self.connection.execute(
                check_query, {"governing_body_id": governing_body_id}
            )
            row = result.fetchone()
            if row is None:
                logger.error(
                    f"Failed to check conferences for governing body {governing_body_id}"
                )
                return False
            count = row[0]

            if count > 0:
                logger.warning(
                    f"Cannot delete governing body {governing_body_id}: has {count} related conferences"
                )
                return False

            # 関連する会議体がなければ削除
            delete_query = text("""
                DELETE FROM governing_bodies
                WHERE id = :governing_body_id
            """)

            self.connection.execute(
                delete_query, {"governing_body_id": governing_body_id}
            )
            self.connection.commit()
            logger.info(f"Deleted governing body ID: {governing_body_id}")
            return True

        except SQLAlchemyError as e:
            self.connection.rollback()
            logger.error(f"Database error deleting governing body: {e}")
            raise DeleteError(
                f"Failed to delete governing body with ID {governing_body_id}",
                {"governing_body_id": governing_body_id, "error": str(e)},
            ) from e
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Unexpected error deleting governing body: {e}")
            raise DeleteError(
                f"Unexpected error deleting governing body with ID {governing_body_id}",
                {"governing_body_id": governing_body_id, "error": str(e)},
            ) from e

    def get_type_options(self) -> list[str]:
        """開催主体の種別オプションを取得"""
        return ["国", "都道府県", "市町村"]
