"""Repository for extracted parliamentary group members"""

import logging

from sqlalchemy import text

from src.database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ExtractedParliamentaryGroupMemberRepository(BaseRepository):
    """抽出された議員団メンバー情報のリポジトリ"""

    def __init__(self):
        super().__init__(use_session=False)  # Uses engine for backward compatibility

    def create_extracted_member(
        self,
        parliamentary_group_id: int,
        extracted_name: str,
        extracted_role: str | None = None,
        extracted_party_name: str | None = None,
        extracted_electoral_district: str | None = None,
        extracted_profile_url: str | None = None,
        source_url: str | None = None,
    ) -> dict | None:
        """抽出された議員団メンバーを作成"""
        query = text("""
            INSERT INTO extracted_parliamentary_group_members (
                parliamentary_group_id, extracted_name, extracted_role,
                extracted_party_name, extracted_electoral_district,
                extracted_profile_url, source_url
            ) VALUES (
                :parliamentary_group_id, :extracted_name, :extracted_role,
                :extracted_party_name, :extracted_electoral_district,
                :extracted_profile_url, :source_url
            )
            ON CONFLICT (parliamentary_group_id, extracted_name)
            DO UPDATE SET
                extracted_role = EXCLUDED.extracted_role,
                extracted_party_name = EXCLUDED.extracted_party_name,
                extracted_electoral_district = EXCLUDED.extracted_electoral_district,
                extracted_profile_url = EXCLUDED.extracted_profile_url,
                source_url = EXCLUDED.source_url,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
        """)

        with self.transaction() as conn:
            result = conn.execute(
                query,
                {
                    "parliamentary_group_id": parliamentary_group_id,
                    "extracted_name": extracted_name,
                    "extracted_role": extracted_role,
                    "extracted_party_name": extracted_party_name,
                    "extracted_electoral_district": extracted_electoral_district,
                    "extracted_profile_url": extracted_profile_url,
                    "source_url": source_url,
                },
            )
            row = result.fetchone()
            return self._row_to_dict(row, result.keys()) if row else None

    def get_pending_members(
        self, parliamentary_group_id: int | None = None
    ) -> list[dict]:
        """未処理の抽出メンバーを取得"""
        query = text("""
            SELECT epgm.*, pg.name as parliamentary_group_name
            FROM extracted_parliamentary_group_members epgm
            JOIN parliamentary_groups pg ON epgm.parliamentary_group_id = pg.id
            WHERE epgm.matching_status = 'pending'
        """)
        params = {}

        if parliamentary_group_id:
            query = text(str(query) + " AND epgm.parliamentary_group_id = :group_id")
            params["group_id"] = parliamentary_group_id

        query = text(str(query) + " ORDER BY epgm.extracted_name")

        with self.engine.connect() as conn:
            result = conn.execute(query, params)
            return [self._row_to_dict(row, result.keys()) for row in result]

    def update_matching_result(
        self,
        extracted_member_id: int,
        matched_politician_id: int | None,
        matching_status: str,
        matching_confidence: float | None = None,
        matching_notes: str | None = None,
    ) -> bool:
        """マッチング結果を更新"""
        query = text("""
            UPDATE extracted_parliamentary_group_members
            SET matched_politician_id = :matched_politician_id,
                matching_status = :matching_status,
                matching_confidence = :matching_confidence,
                matching_notes = :matching_notes,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """)

        with self.transaction() as conn:
            result = conn.execute(
                query,
                {
                    "id": extracted_member_id,
                    "matched_politician_id": matched_politician_id,
                    "matching_status": matching_status,
                    "matching_confidence": matching_confidence,
                    "matching_notes": matching_notes,
                },
            )
            return result.rowcount > 0

    def get_matched_members(
        self, parliamentary_group_id: int | None = None
    ) -> list[dict]:
        """マッチング済みメンバーを取得"""
        query = text("""
            SELECT epgm.*,
                   pg.name as parliamentary_group_name,
                   p.name as politician_name
            FROM extracted_parliamentary_group_members epgm
            JOIN parliamentary_groups pg ON epgm.parliamentary_group_id = pg.id
            LEFT JOIN politicians p ON epgm.matched_politician_id = p.id
            WHERE epgm.matching_status = 'matched'
        """)
        params = {}

        if parliamentary_group_id:
            query = text(str(query) + " AND epgm.parliamentary_group_id = :group_id")
            params["group_id"] = parliamentary_group_id

        query = text(str(query) + " ORDER BY epgm.extracted_name")

        with self.engine.connect() as conn:
            result = conn.execute(query, params)
            return [self._row_to_dict(row, result.keys()) for row in result]

    def clear_extracted_members(self, parliamentary_group_id: int) -> int:
        """特定の議員団の抽出データをクリア"""
        query = text("""
            DELETE FROM extracted_parliamentary_group_members
            WHERE parliamentary_group_id = :group_id
        """)

        with self.transaction() as conn:
            result = conn.execute(query, {"group_id": parliamentary_group_id})
            return result.rowcount

    def get_extraction_summary(self, parliamentary_group_id: int) -> dict:
        """議員団の抽出状況サマリーを取得"""
        query = text("""
            SELECT
                COUNT(*) as total_count,
                COUNT(CASE WHEN matching_status = 'pending' THEN 1 END)
                    as pending_count,
                COUNT(CASE WHEN matching_status = 'matched' THEN 1 END)
                    as matched_count,
                COUNT(CASE WHEN matching_status = 'needs_review' THEN 1 END)
                    as needs_review_count,
                COUNT(CASE WHEN matching_status = 'no_match' THEN 1 END)
                    as no_match_count
            FROM extracted_parliamentary_group_members
            WHERE parliamentary_group_id = :group_id
        """)

        with self.engine.connect() as conn:
            result = conn.execute(query, {"group_id": parliamentary_group_id})
            row = result.fetchone()
            return self._row_to_dict(row, result.keys()) if row else {}

    def _row_to_dict(self, row, columns) -> dict:
        """Rowオブジェクトを辞書に変換する"""
        if row is None:
            return {}
        return dict(zip(columns, row, strict=False))
