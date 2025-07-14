"""Repository for managing conferences"""

import logging

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


class ConferenceRepository:
    """会議体テーブルの操作を行うリポジトリクラス"""

    def __init__(self):
        self.engine = get_db_engine()
        self.connection = None

    def __enter__(self):
        self.connection = self.engine.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.close()

    def close(self):
        """接続を閉じる"""
        if self.connection:
            self.connection.close()

    def get_all_conferences(self) -> list[dict]:
        """すべての会議体を取得

        Raises:
            QueryError: If database query fails
            ConnectionError: If database connection fails
        """
        try:
            if not self.connection:
                self.connection = self.engine.connect()

            query = text("""
                SELECT
                    c.id,
                    c.name,
                    c.type,
                    c.governing_body_id,
                    c.members_introduction_url,
                    gb.name as governing_body_name,
                    gb.type as governing_body_type
                FROM conferences c
                LEFT JOIN governing_bodies gb ON c.governing_body_id = gb.id
                ORDER BY COALESCE(gb.name, ''), c.name
            """)

            result = self.connection.execute(query)
            conferences = []
            for row in result:
                conferences.append(
                    {
                        "id": row.id,
                        "name": row.name,
                        "type": row.type,
                        "governing_body_id": row.governing_body_id,
                        "members_introduction_url": row.members_introduction_url,
                        "governing_body_name": row.governing_body_name,
                        "governing_body_type": row.governing_body_type,
                    }
                )

            return conferences
        except SQLAlchemyError as e:
            logger.error(f"Database error getting all conferences: {e}")
            raise QueryError(
                "Failed to retrieve conferences",
                {"error": str(e)},
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error getting all conferences: {e}")
            raise DatabaseError(
                "Unexpected error retrieving conferences",
                {"error": str(e)},
            ) from e

    def get_conference_by_id(self, conference_id: int) -> dict | None:
        """IDで会議体を取得

        Raises:
            QueryError: If database query fails
        """
        try:
            if not self.connection:
                self.connection = self.engine.connect()

            query = text("""
                SELECT
                    c.id,
                    c.name,
                    c.type,
                    c.governing_body_id,
                    c.members_introduction_url,
                    gb.name as governing_body_name,
                    gb.type as governing_body_type
                FROM conferences c
                LEFT JOIN governing_bodies gb ON c.governing_body_id = gb.id
                WHERE c.id = :conference_id
            """)

            result = self.connection.execute(query, {"conference_id": conference_id})
            row = result.fetchone()

            if row:
                return {
                    "id": row.id,
                    "name": row.name,
                    "type": row.type,
                    "governing_body_id": row.governing_body_id,
                    "members_introduction_url": row.members_introduction_url,
                    "governing_body_name": row.governing_body_name,
                    "governing_body_type": row.governing_body_type,
                }

            return None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting conference {conference_id}: {e}")
            raise QueryError(
                f"Failed to retrieve conference with ID {conference_id}",
                {"conference_id": conference_id, "error": str(e)},
            ) from e

    def get_conferences_by_governing_body(self, governing_body_id: int) -> list[dict]:
        """開催主体IDで会議体を取得"""
        if not self.connection:
            self.connection = self.engine.connect()

        query = text("""
            SELECT
                c.id,
                c.name,
                c.type,
                c.governing_body_id,
                c.members_introduction_url,
                gb.name as governing_body_name,
                gb.type as governing_body_type
            FROM conferences c
            LEFT JOIN governing_bodies gb ON c.governing_body_id = gb.id
            WHERE c.governing_body_id = :governing_body_id
            ORDER BY c.name
        """)

        result = self.connection.execute(
            query, {"governing_body_id": governing_body_id}
        )
        conferences = []
        for row in result:
            conferences.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "type": row.type,
                    "governing_body_id": row.governing_body_id,
                    "members_introduction_url": row.members_introduction_url,
                    "governing_body_name": row.governing_body_name,
                    "governing_body_type": row.governing_body_type,
                }
            )

        return conferences

    def create_conference(
        self, name: str, governing_body_id: int, type: str | None = None
    ) -> int | None:
        """新しい会議体を作成"""
        if not self.connection:
            self.connection = self.engine.connect()

        try:
            query = text("""
                INSERT INTO conferences (name, type, governing_body_id)
                VALUES (:name, :type, :governing_body_id)
                RETURNING id
            """)

            result = self.connection.execute(
                query,
                {"name": name, "type": type, "governing_body_id": governing_body_id},
            )

            self.connection.commit()
            row = result.fetchone()
            if row is None:
                logger.error("Failed to get conference ID after creation")
                return None
            conference_id = row[0]
            logger.info(f"Created conference with ID: {conference_id}")
            return conference_id

        except SQLIntegrityError as e:
            self.connection.rollback()
            logger.error(f"Integrity error creating conference: {e}")
            raise IntegrityError(
                f"Conference '{name}' may already exist or violates constraints",
                {"name": name, "governing_body_id": governing_body_id, "error": str(e)},
            ) from e
        except SQLAlchemyError as e:
            self.connection.rollback()
            logger.error(f"Database error creating conference: {e}")
            raise SaveError(
                f"Failed to create conference '{name}'",
                {"name": name, "governing_body_id": governing_body_id, "error": str(e)},
            ) from e
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Unexpected error creating conference: {e}")
            raise SaveError(
                f"Unexpected error creating conference '{name}'",
                {"name": name, "error": str(e)},
            ) from e

    def update_conference(
        self,
        conference_id: int,
        name: str | None = None,
        type: str | None = None,
        governing_body_id: int | None = None,
        members_introduction_url: str | None = None,
    ) -> bool:
        """会議体を更新（指定されたフィールドのみ更新）"""
        if not self.connection:
            self.connection = self.engine.connect()

        try:
            # 更新するフィールドを動的に構築
            update_fields = []
            params = {"conference_id": conference_id}

            if name is not None:
                update_fields.append("name = :name")
                params["name"] = str(name)

            if type is not None:
                update_fields.append("type = :type")
                params["type"] = str(type)

            if governing_body_id is not None:
                update_fields.append("governing_body_id = :governing_body_id")
                params["governing_body_id"] = governing_body_id

            if members_introduction_url is not None:
                update_fields.append(
                    "members_introduction_url = :members_introduction_url"
                )
                params["members_introduction_url"] = str(members_introduction_url)

            # 更新フィールドがない場合は何もしない
            if not update_fields:
                return True

            # 常にupdated_atを更新
            update_fields.append("updated_at = CURRENT_TIMESTAMP")

            query = text(f"""
                UPDATE conferences
                SET {", ".join(update_fields)}
                WHERE id = :conference_id
            """)

            self.connection.execute(query, params)
            self.connection.commit()
            logger.info(f"Updated conference ID: {conference_id}")
            return True

        except SQLAlchemyError as e:
            self.connection.rollback()
            logger.error(f"Database error updating conference: {e}")
            raise UpdateError(
                f"Failed to update conference ID {conference_id}",
                {"conference_id": conference_id, "error": str(e)},
            ) from e
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Unexpected error updating conference: {e}")
            raise UpdateError(
                f"Unexpected error updating conference ID {conference_id}",
                {"conference_id": conference_id, "error": str(e)},
            ) from e

    def update_conference_members_url(
        self, conference_id: int, members_introduction_url: str | None
    ) -> bool:
        """会議体の議員紹介URLを更新"""
        if not self.connection:
            self.connection = self.engine.connect()

        try:
            query = text("""
                UPDATE conferences
                SET members_introduction_url = :members_introduction_url,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :conference_id
            """)

            self.connection.execute(
                query,
                {
                    "conference_id": conference_id,
                    "members_introduction_url": members_introduction_url,
                },
            )

            self.connection.commit()
            logger.info(f"Updated members URL for conference ID: {conference_id}")
            return True

        except SQLAlchemyError as e:
            self.connection.rollback()
            logger.error(f"Database error updating conference members URL: {e}")
            raise UpdateError(
                f"Failed to update members URL for conference ID {conference_id}",
                {"conference_id": conference_id, "error": str(e)},
            ) from e

    def delete_conference(self, conference_id: int) -> bool:
        """会議体を削除"""
        if not self.connection:
            self.connection = self.engine.connect()

        try:
            # まず、この会議体に関連する会議があるかチェック
            check_query = text("""
                SELECT COUNT(*) as count
                FROM meetings
                WHERE conference_id = :conference_id
            """)

            result = self.connection.execute(
                check_query, {"conference_id": conference_id}
            )
            row = result.fetchone()
            if row is None:
                logger.error(f"Failed to check meetings for conference {conference_id}")
                return False
            count = row.count

            if int(count) > 0:
                logger.warning(
                    f"Cannot delete conference {conference_id}: "
                    f"has {count} related meetings"
                )
                return False

            # 関連する会議がなければ削除
            delete_query = text("""
                DELETE FROM conferences
                WHERE id = :conference_id
            """)

            self.connection.execute(delete_query, {"conference_id": conference_id})
            self.connection.commit()
            logger.info(f"Deleted conference ID: {conference_id}")
            return True

        except SQLAlchemyError as e:
            self.connection.rollback()
            logger.error(f"Database error deleting conference: {e}")
            raise DeleteError(
                f"Failed to delete conference ID {conference_id}",
                {"conference_id": conference_id, "error": str(e)},
            ) from e
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Unexpected error deleting conference: {e}")
            raise DeleteError(
                f"Unexpected error deleting conference ID {conference_id}",
                {"conference_id": conference_id, "error": str(e)},
            ) from e

    def get_governing_bodies(self) -> list[dict]:
        """すべての開催主体を取得

        Raises:
            QueryError: If database query fails
        """
        try:
            if not self.connection:
                self.connection = self.engine.connect()

            query = text("""
                SELECT id, name, type
                FROM governing_bodies
                ORDER BY type, name
            """)

            result = self.connection.execute(query)
            governing_bodies = []
            for row in result:
                governing_bodies.append(
                    {"id": row.id, "name": row.name, "type": row.type}
                )

            return governing_bodies
        except SQLAlchemyError as e:
            logger.error(f"Database error getting governing bodies: {e}")
            raise QueryError(
                "Failed to retrieve governing bodies",
                {"error": str(e)},
            ) from e
