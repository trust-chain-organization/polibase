"""Repository for managing politician data"""

import logging

from sqlalchemy import text

from src.database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class PoliticianRepository(BaseRepository):
    def __init__(self):
        super().__init__(use_session=False)  # Uses engine for backward compatibility

    def create_politician(
        self,
        name: str,
        political_party_id: int,
        position: str | None = None,
        prefecture: str | None = None,
        electoral_district: str | None = None,
        profile_url: str | None = None,
        party_position: str | None = None,
    ) -> int | None:
        """新しい政治家を作成（既存の場合は更新）"""
        with self.transaction() as conn:
            # 既存の政治家をチェック（名前と政党でマッチング）
            check_query = """
                SELECT id, position, prefecture, electoral_district,
                       profile_url, party_position
                FROM politicians
                WHERE name = :name AND political_party_id = :party_id
            """
            existing = conn.execute(
                text(check_query), {"name": name, "party_id": political_party_id}
            ).fetchone()

            if existing:
                # 既存レコードがある場合、更新が必要かチェック
                needs_update = False
                update_fields = {}

                # 各フィールドを比較
                if position and position != existing.position:
                    update_fields["position"] = position
                    needs_update = True
                if prefecture and prefecture != existing.prefecture:
                    update_fields["prefecture"] = prefecture
                    needs_update = True
                if (
                    electoral_district
                    and electoral_district != existing.electoral_district
                ):
                    update_fields["electoral_district"] = electoral_district
                    needs_update = True
                if profile_url and profile_url != existing.profile_url:
                    update_fields["profile_url"] = profile_url
                    needs_update = True
                if party_position and party_position != existing.party_position:
                    update_fields["party_position"] = party_position
                    needs_update = True

                if needs_update:
                    # 更新を実行
                    set_clause = ", ".join(
                        [f"{field} = :{field}" for field in update_fields]
                    )
                    update_query = text(f"""
                        UPDATE politicians
                        SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                        WHERE id = :id
                    """)
                    update_fields["id"] = existing.id
                    conn.execute(update_query, update_fields)
                    logger.info(f"Updated politician: {name} (id: {existing.id})")
                else:
                    logger.info(
                        f"Politician {name} already exists with id: {existing.id}, "
                        "no update needed"
                    )

                return existing.id

            # 新規作成
            insert_query = text("""
                INSERT INTO politicians (name, political_party_id, position,
                                       prefecture, electoral_district, profile_url,
                                       party_position, speaker_id)
                VALUES (:name, :party_id, :position, :prefecture,
                        :electoral_district, :profile_url, :party_position, NULL)
                RETURNING id
            """)

            result = conn.execute(
                insert_query,
                {
                    "name": name,
                    "party_id": political_party_id,
                    "position": position,
                    "prefecture": prefecture,
                    "electoral_district": electoral_district,
                    "profile_url": profile_url,
                    "party_position": party_position,
                },
            )

            politician_id = result.fetchone().id
            logger.info(f"Created new politician: {name} with id: {politician_id}")
            return politician_id

    def bulk_create_politicians(
        self, politicians_data: list[dict]
    ) -> dict[str, list[int]]:
        """複数の政治家を一括作成・更新"""
        stats = {"created": [], "updated": [], "skipped": [], "errors": []}

        for data in politicians_data:
            # 処理前の状態を確認
            was_existing = self.exists(
                "politicians",
                {
                    "name": data.get("name"),
                    "political_party_id": data.get("political_party_id"),
                },
            )

            # create_politicianは内部で更新/作成を判断
            politician_id = self.create_politician(
                name=data.get("name"),
                political_party_id=data.get("political_party_id"),
                position=data.get("position"),
                prefecture=data.get("prefecture"),
                electoral_district=data.get("electoral_district"),
                profile_url=data.get("profile_url"),
                party_position=data.get("party_position"),
            )

            if politician_id:
                if was_existing:
                    # ログを確認して更新されたかスキップされたか判断
                    # 簡易的に、既存の場合は更新としてカウント
                    stats["updated"].append(politician_id)
                else:
                    stats["created"].append(politician_id)
            else:
                stats["errors"].append(data.get("name", "Unknown"))

        logger.info(
            f"Bulk operation completed - Created: {len(stats['created'])}, "
            f"Updated: {len(stats['updated'])}, Errors: {len(stats['errors'])}"
        )

        return stats

    def get_politicians_by_party(self, party_id: int) -> list[dict]:
        """特定の政党の政治家を取得"""
        query = """
            SELECT id, name, position, prefecture, electoral_district, profile_url
            FROM politicians
            WHERE political_party_id = :party_id
            ORDER BY name
        """
        return self.fetch_as_dict(query, {"party_id": party_id})

    def update_politician(self, politician_id: int, **kwargs) -> bool:
        """政治家情報を更新"""
        try:
            # 更新可能なフィールドをフィルタリング
            allowed_fields = [
                "name",
                "position",
                "prefecture",
                "electoral_district",
                "profile_url",
                "political_party_id",
            ]
            update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}

            if not update_fields:
                return True

            rows_affected = self.update(
                table="politicians", data=update_fields, where={"id": politician_id}
            )

            logger.info(f"Updated politician id: {politician_id}")
            return rows_affected > 0

        except Exception as e:
            logger.error(f"Error updating politician: {e}")
            return False

    def find_by_name(self, name: str) -> list[dict]:
        """名前で政治家を検索"""
        query = """
            SELECT p.id, p.name, p.political_party_id, p.position,
                   p.prefecture, p.electoral_district, p.profile_url,
                   pp.name as political_party_name
            FROM politicians p
            LEFT JOIN political_parties pp ON p.political_party_id = pp.id
            WHERE p.name = :name
            ORDER BY p.id
        """
        return self.fetch_as_dict(query, {"name": name})

    def search_by_name(self, name: str) -> list[dict]:
        """名前で政治家を検索（部分一致を含む）"""
        query = """
            SELECT p.id, p.name, p.political_party_id, p.position,
                   p.prefecture, p.electoral_district, p.profile_url,
                   pp.name as party_name
            FROM politicians p
            LEFT JOIN political_parties pp ON p.political_party_id = pp.id
            WHERE p.name = :name OR p.name LIKE :partial_name
            ORDER BY
                CASE WHEN p.name = :name THEN 0 ELSE 1 END,
                p.name
        """
        return self.fetch_as_dict(query, {"name": name, "partial_name": f"%{name}%"})

    # close() method is inherited from BaseRepository
