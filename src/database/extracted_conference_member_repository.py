"""Repository for managing extracted conference member data"""

import logging

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError as SQLIntegrityError
from sqlalchemy.exc import SQLAlchemyError

from src.config.database import get_db_engine
from src.exceptions import (
    IntegrityError,
    QueryError,
    SaveError,
)

logger = logging.getLogger(__name__)


class ExtractedConferenceMemberRepository:
    """抽出された会議体メンバー情報テーブルの操作を行うリポジトリクラス"""

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

    def create_extracted_member(
        self,
        conference_id: int,
        extracted_name: str,
        source_url: str,
        extracted_role: str | None = None,
        extracted_party_name: str | None = None,
        additional_info: str | None = None,
    ) -> int | None:
        """抽出されたメンバー情報を作成"""
        if not self.connection:
            self.connection = self.engine.connect()

        try:
            query = text("""
                INSERT INTO extracted_conference_members
                (conference_id, extracted_name, extracted_role, extracted_party_name,
                 source_url, additional_info, extracted_at)
                VALUES (:conference_id, :extracted_name, :extracted_role,
                        :extracted_party_name, :source_url, :additional_info,
                        CURRENT_TIMESTAMP)
                RETURNING id
            """)

            result = self.connection.execute(
                query,
                {
                    "conference_id": conference_id,
                    "extracted_name": extracted_name,
                    "extracted_role": extracted_role,
                    "extracted_party_name": extracted_party_name,
                    "source_url": source_url,
                    "additional_info": additional_info,
                },
            )

            self.connection.commit()
            member_id = result.fetchone()[0]
            logger.info(f"Created extracted member with ID: {member_id}")
            return member_id

        except SQLIntegrityError as e:
            self.connection.rollback()
            logger.error(f"Integrity error creating extracted member: {e}")
            raise IntegrityError(
                f"Extracted member '{extracted_name}' may already exist",
                {
                    "extracted_name": extracted_name,
                    "conference_id": conference_id,
                    "error": str(e),
                },
            ) from e
        except SQLAlchemyError as e:
            self.connection.rollback()
            logger.error(f"Database error creating extracted member: {e}")
            raise SaveError(
                f"Failed to create extracted member '{extracted_name}'",
                {
                    "extracted_name": extracted_name,
                    "conference_id": conference_id,
                    "error": str(e),
                },
            ) from e
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Unexpected error creating extracted member: {e}")
            raise SaveError(
                f"Unexpected error creating extracted member '{extracted_name}'",
                {"extracted_name": extracted_name, "error": str(e)},
            ) from e

    def get_pending_members(self, conference_id: int | None = None) -> list[dict]:
        """未処理のメンバー情報を取得"""
        if not self.connection:
            self.connection = self.engine.connect()

        query = text("""
            SELECT
                ecm.id,
                ecm.conference_id,
                ecm.extracted_name,
                ecm.extracted_role,
                ecm.extracted_party_name,
                ecm.source_url,
                ecm.additional_info,
                ecm.extracted_at,
                c.name as conference_name,
                gb.name as governing_body_name
            FROM extracted_conference_members ecm
            JOIN conferences c ON ecm.conference_id = c.id
            JOIN governing_bodies gb ON c.governing_body_id = gb.id
            WHERE ecm.matching_status = 'pending'
            {conference_filter}
            ORDER BY ecm.extracted_at DESC
        """)

        if conference_id:
            query_str = str(query).format(
                conference_filter="AND ecm.conference_id = :conference_id"
            )
            params = {"conference_id": conference_id}
        else:
            query_str = str(query).format(conference_filter="")
            params = {}

        result = self.connection.execute(text(query_str), params)

        members = []
        for row in result:
            members.append(
                {
                    "id": row.id,
                    "conference_id": row.conference_id,
                    "extracted_name": row.extracted_name,
                    "extracted_role": row.extracted_role,
                    "extracted_party_name": row.extracted_party_name,
                    "source_url": row.source_url,
                    "additional_info": row.additional_info,
                    "extracted_at": row.extracted_at,
                    "conference_name": row.conference_name,
                    "governing_body_name": row.governing_body_name,
                }
            )

        return members

    def update_matching_result(
        self,
        member_id: int,
        matched_politician_id: int | None,
        matching_confidence: float | None,
        matching_status: str,
    ) -> bool:
        """マッチング結果を更新"""
        if not self.connection:
            self.connection = self.engine.connect()

        try:
            query = text("""
                UPDATE extracted_conference_members
                SET matched_politician_id = :politician_id,
                    matching_confidence = :confidence,
                    matching_status = :status,
                    matched_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :member_id
            """)

            self.connection.execute(
                query,
                {
                    "member_id": member_id,
                    "politician_id": matched_politician_id,
                    "confidence": matching_confidence,
                    "status": matching_status,
                },
            )

            self.connection.commit()
            logger.info(f"Updated matching result for member ID: {member_id}")
            return True

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error updating matching result: {e}")
            return False

    def get_matched_members(self, conference_id: int | None = None) -> list[dict]:
        """マッチング済みのメンバー情報を取得"""
        if not self.connection:
            self.connection = self.engine.connect()

        query = text("""
            SELECT
                ecm.id,
                ecm.conference_id,
                ecm.extracted_name,
                ecm.extracted_role,
                ecm.extracted_party_name,
                ecm.matched_politician_id,
                ecm.matching_confidence,
                ecm.matching_status,
                ecm.matched_at,
                p.name as politician_name,
                pp.name as politician_party_name,
                c.name as conference_name
            FROM extracted_conference_members ecm
            JOIN conferences c ON ecm.conference_id = c.id
            LEFT JOIN politicians p ON ecm.matched_politician_id = p.id
            LEFT JOIN political_parties pp ON p.political_party_id = pp.id
            WHERE ecm.matching_status = 'matched'
            {conference_filter}
            ORDER BY ecm.matched_at DESC
        """)

        if conference_id:
            query_str = str(query).format(
                conference_filter="AND ecm.conference_id = :conference_id"
            )
            params = {"conference_id": conference_id}
        else:
            query_str = str(query).format(conference_filter="")
            params = {}

        result = self.connection.execute(text(query_str), params)

        members = []
        for row in result:
            members.append(
                {
                    "id": row.id,
                    "conference_id": row.conference_id,
                    "extracted_name": row.extracted_name,
                    "extracted_role": row.extracted_role,
                    "extracted_party_name": row.extracted_party_name,
                    "matched_politician_id": row.matched_politician_id,
                    "matching_confidence": row.matching_confidence,
                    "matching_status": row.matching_status,
                    "matched_at": row.matched_at,
                    "politician_name": row.politician_name,
                    "politician_party_name": row.politician_party_name,
                    "conference_name": row.conference_name,
                }
            )

        return members

    def delete_extracted_members(self, conference_id: int) -> int:
        """特定の会議体の抽出データを削除"""
        if not self.connection:
            self.connection = self.engine.connect()

        try:
            query = text("""
                DELETE FROM extracted_conference_members
                WHERE conference_id = :conference_id
            """)

            result = self.connection.execute(query, {"conference_id": conference_id})
            self.connection.commit()

            deleted_count = result.rowcount
            logger.info(
                f"Deleted {deleted_count} extracted members "
                f"for conference {conference_id}"
            )
            return deleted_count

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Error deleting extracted members: {e}")
            return 0

    def get_extraction_summary(self) -> dict:
        """抽出状況のサマリーを取得

        Raises:
            QueryError: If database query fails
        """
        try:
            if not self.connection:
                self.connection = self.engine.connect()

            query = text("""
                SELECT
                    matching_status,
                    COUNT(*) as count
                FROM extracted_conference_members
                GROUP BY matching_status
            """)

            result = self.connection.execute(query)

            summary = {
                "pending": 0,
                "matched": 0,
                "no_match": 0,
                "needs_review": 0,
                "total": 0,
            }

            for row in result:
                if row.matching_status in summary:
                    summary[row.matching_status] = row.count
                summary["total"] += row.count

            return summary
        except SQLAlchemyError as e:
            logger.error(f"Database error getting extraction summary: {e}")
            raise QueryError(
                "Failed to retrieve extraction summary",
                {"error": str(e)},
            ) from e
