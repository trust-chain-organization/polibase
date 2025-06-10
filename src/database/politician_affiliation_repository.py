"""Repository for managing politician affiliations"""

import logging
from datetime import date

from sqlalchemy import text

from src.config.database import get_db_engine

logger = logging.getLogger(__name__)


class PoliticianAffiliationRepository:
    """政治家の議会所属情報テーブルの操作を行うリポジトリクラス"""

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

    def create_affiliation(
        self,
        politician_id: int,
        conference_id: int,
        start_date: date,
        end_date: date | None = None,
        role: str | None = None,
    ) -> int | None:
        """新しい所属情報を作成"""
        if not self.connection:
            self.connection = self.engine.connect()

        try:
            # 既存の所属情報をチェック（同じ政治家・会議体・期間の重複を防ぐ）
            check_query = text("""
                SELECT id FROM politician_affiliations
                WHERE politician_id = :politician_id
                AND conference_id = :conference_id
                AND start_date = :start_date
                AND (end_date IS NULL OR end_date = :end_date)
            """)

            result = self.connection.execute(
                check_query,
                {
                    "politician_id": politician_id,
                    "conference_id": conference_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )

            if result.fetchone():
                logger.warning(
                    f"Affiliation already exists for politician {politician_id} "
                    f"in conference {conference_id} starting {start_date}"
                )
                return None

            # 新規作成
            insert_query = text("""
                INSERT INTO politician_affiliations
                (politician_id, conference_id, start_date, end_date, role)
                VALUES (:politician_id, :conference_id, :start_date, :end_date, :role)
                RETURNING id
            """)

            result = self.connection.execute(
                insert_query,
                {
                    "politician_id": politician_id,
                    "conference_id": conference_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "role": role,
                },
            )

            self.connection.commit()
            affiliation_id = result.fetchone()[0]
            logger.info(f"Created affiliation with ID: {affiliation_id}")
            return affiliation_id

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error creating affiliation: {e}")
            return None

    def update_affiliation_role(self, affiliation_id: int, role: str) -> bool:
        """所属情報の役職を更新"""
        if not self.connection:
            self.connection = self.engine.connect()

        try:
            query = text("""
                UPDATE politician_affiliations
                SET role = :role, updated_at = CURRENT_TIMESTAMP
                WHERE id = :affiliation_id
            """)

            self.connection.execute(
                query, {"affiliation_id": affiliation_id, "role": role}
            )

            self.connection.commit()
            logger.info(f"Updated role for affiliation ID: {affiliation_id}")
            return True

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error updating affiliation role: {e}")
            return False

    def get_affiliations_by_conference(self, conference_id: int) -> list[dict]:
        """会議体IDで所属情報を取得"""
        if not self.connection:
            self.connection = self.engine.connect()

        query = text("""
            SELECT
                pa.id,
                pa.politician_id,
                pa.conference_id,
                pa.start_date,
                pa.end_date,
                pa.role,
                p.name as politician_name,
                pp.name as party_name
            FROM politician_affiliations pa
            JOIN politicians p ON pa.politician_id = p.id
            LEFT JOIN political_parties pp ON p.political_party_id = pp.id
            WHERE pa.conference_id = :conference_id
            AND (pa.end_date IS NULL OR pa.end_date >= CURRENT_DATE)
            ORDER BY pa.role, p.name
        """)

        result = self.connection.execute(query, {"conference_id": conference_id})
        affiliations = []
        for row in result:
            affiliations.append(
                {
                    "id": row.id,
                    "politician_id": row.politician_id,
                    "conference_id": row.conference_id,
                    "start_date": row.start_date,
                    "end_date": row.end_date,
                    "role": row.role,
                    "politician_name": row.politician_name,
                    "party_name": row.party_name,
                }
            )

        return affiliations

    def get_affiliations_by_politician(self, politician_id: int) -> list[dict]:
        """政治家IDで所属情報を取得"""
        if not self.connection:
            self.connection = self.engine.connect()

        query = text("""
            SELECT
                pa.id,
                pa.politician_id,
                pa.conference_id,
                pa.start_date,
                pa.end_date,
                pa.role,
                c.name as conference_name,
                gb.name as governing_body_name
            FROM politician_affiliations pa
            JOIN conferences c ON pa.conference_id = c.id
            JOIN governing_bodies gb ON c.governing_body_id = gb.id
            WHERE pa.politician_id = :politician_id
            ORDER BY pa.start_date DESC
        """)

        result = self.connection.execute(query, {"politician_id": politician_id})
        affiliations = []
        for row in result:
            affiliations.append(
                {
                    "id": row.id,
                    "politician_id": row.politician_id,
                    "conference_id": row.conference_id,
                    "start_date": row.start_date,
                    "end_date": row.end_date,
                    "role": row.role,
                    "conference_name": row.conference_name,
                    "governing_body_name": row.governing_body_name,
                }
            )

        return affiliations

    def delete_affiliation(self, affiliation_id: int) -> bool:
        """所属情報を削除"""
        if not self.connection:
            self.connection = self.engine.connect()

        try:
            query = text("""
                DELETE FROM politician_affiliations
                WHERE id = :affiliation_id
            """)

            self.connection.execute(query, {"affiliation_id": affiliation_id})
            self.connection.commit()
            logger.info(f"Deleted affiliation ID: {affiliation_id}")
            return True

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error deleting affiliation: {e}")
            return False

    def end_affiliation(self, affiliation_id: int, end_date: date) -> bool:
        """所属情報を終了させる（end_dateを設定）"""
        if not self.connection:
            self.connection = self.engine.connect()

        try:
            query = text("""
                UPDATE politician_affiliations
                SET end_date = :end_date, updated_at = CURRENT_TIMESTAMP
                WHERE id = :affiliation_id
            """)

            self.connection.execute(
                query, {"affiliation_id": affiliation_id, "end_date": end_date}
            )

            self.connection.commit()
            logger.info(f"Ended affiliation ID: {affiliation_id} on {end_date}")
            return True

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error ending affiliation: {e}")
            return False

    def upsert_affiliation(
        self,
        politician_id: int,
        conference_id: int,
        start_date: date,
        end_date: date | None = None,
        role: str | None = None,
    ) -> int:
        """所属情報をUPSERT（存在すれば更新、なければ作成）"""
        if not self.connection:
            self.connection = self.engine.connect()

        try:
            # 既存のレコードを確認
            check_query = text("""
                SELECT id FROM politician_affiliations
                WHERE politician_id = :politician_id
                AND conference_id = :conference_id
                AND start_date = :start_date
            """)

            result = self.connection.execute(
                check_query,
                {
                    "politician_id": politician_id,
                    "conference_id": conference_id,
                    "start_date": start_date,
                },
            )

            existing = result.fetchone()

            if existing:
                # 更新
                update_query = text("""
                    UPDATE politician_affiliations
                    SET end_date = :end_date,
                        role = :role,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                """)

                self.connection.execute(
                    update_query,
                    {
                        "id": existing.id,
                        "end_date": end_date,
                        "role": role,
                    },
                )
                self.connection.commit()
                logger.info(f"Updated affiliation ID: {existing.id}")
                return existing.id
            else:
                # 新規作成
                return self.create_affiliation(
                    politician_id, conference_id, start_date, end_date, role
                )

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error upserting affiliation: {e}")
            raise
