"""Repository for managing conferences"""

import logging

from sqlalchemy import text

from src.config.database import get_db_engine

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
        """すべての会議体を取得"""
        if not self.connection:
            self.connection = self.engine.connect()

        query = text("""
            SELECT
                c.id,
                c.name,
                c.type,
                c.governing_body_id,
                gb.name as governing_body_name,
                gb.type as governing_body_type
            FROM conferences c
            JOIN governing_bodies gb ON c.governing_body_id = gb.id
            ORDER BY gb.name, c.name
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
                    "governing_body_name": row.governing_body_name,
                    "governing_body_type": row.governing_body_type,
                }
            )

        return conferences

    def get_conference_by_id(self, conference_id: int) -> dict | None:
        """IDで会議体を取得"""
        if not self.connection:
            self.connection = self.engine.connect()

        query = text("""
            SELECT
                c.id,
                c.name,
                c.type,
                c.governing_body_id,
                gb.name as governing_body_name,
                gb.type as governing_body_type
            FROM conferences c
            JOIN governing_bodies gb ON c.governing_body_id = gb.id
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
                "governing_body_name": row.governing_body_name,
                "governing_body_type": row.governing_body_type,
            }

        return None

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
                gb.name as governing_body_name,
                gb.type as governing_body_type
            FROM conferences c
            JOIN governing_bodies gb ON c.governing_body_id = gb.id
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
            conference_id = result.fetchone()[0]
            logger.info(f"Created conference with ID: {conference_id}")
            return conference_id

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error creating conference: {e}")
            return None

    def update_conference(
        self, conference_id: int, name: str, type: str | None = None
    ) -> bool:
        """会議体を更新"""
        if not self.connection:
            self.connection = self.engine.connect()

        try:
            query = text("""
                UPDATE conferences
                SET name = :name, type = :type, updated_at = CURRENT_TIMESTAMP
                WHERE id = :conference_id
            """)

            self.connection.execute(
                query, {"conference_id": conference_id, "name": name, "type": type}
            )

            self.connection.commit()
            logger.info(f"Updated conference ID: {conference_id}")
            return True

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error updating conference: {e}")
            return False

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
            count = result.fetchone().count

            if count > 0:
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

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error deleting conference: {e}")
            return False

    def get_governing_bodies(self) -> list[dict]:
        """すべての開催主体を取得"""
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
            governing_bodies.append({"id": row.id, "name": row.name, "type": row.type})

        return governing_bodies
