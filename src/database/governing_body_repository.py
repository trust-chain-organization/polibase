"""Repository for managing governing bodies"""

import logging

from sqlalchemy import text

from src.config.database import get_db_engine

logger = logging.getLogger(__name__)


class GoverningBodyRepository:
    """開催主体テーブルの操作を行うリポジトリクラス"""

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

    def get_all_governing_bodies(self) -> list[dict]:
        """すべての開催主体を取得"""
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
        governing_bodies = []
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

    def get_governing_body_by_id(self, governing_body_id: int) -> dict | None:
        """IDで開催主体を取得"""
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

    def get_governing_bodies_by_type(self, gb_type: str) -> list[dict]:
        """種別で開催主体を取得"""
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
        governing_bodies = []
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
            governing_body_id = result.fetchone()[0]
            logger.info(f"Created governing body with ID: {governing_body_id}")
            return governing_body_id

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error creating governing body: {e}")
            return None

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
                    f"Another governing body with same name and type exists: "
                    f"{name} ({gb_type})"
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

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error updating governing body: {e}")
            return False

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
            count = result.fetchone().count

            if count > 0:
                logger.warning(
                    f"Cannot delete governing body {governing_body_id}: "
                    f"has {count} related conferences"
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

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error deleting governing body: {e}")
            return False

    def get_type_options(self) -> list[str]:
        """開催主体の種別オプションを取得"""
        return ["国", "都道府県", "市町村"]
