"""Repository for managing politician data using Pydantic models"""

import logging

from src.database.base_repository import BaseRepository
from src.models.politician import Politician, PoliticianCreate, PoliticianUpdate

logger = logging.getLogger(__name__)


class PoliticianRepositoryV2(BaseRepository):
    """Politician repository with Pydantic model support"""

    def __init__(self):
        super().__init__(use_session=False)

    def create_politician(self, politician: PoliticianCreate) -> Politician | None:
        """新しい政治家を作成（既存の場合は更新）"""
        # 既存の政治家をチェック（名前と政党でマッチング）
        existing = self.get_by_name_and_party(
            politician.name, politician.political_party_id
        )

        if existing:
            # 既存レコードがある場合、更新が必要かチェック
            update_data = PoliticianUpdate()
            needs_update = False

            # 各フィールドを比較
            if politician.position and politician.position != existing.position:
                update_data.position = politician.position
                needs_update = True
            if politician.prefecture and politician.prefecture != existing.prefecture:
                update_data.prefecture = politician.prefecture
                needs_update = True
            if (
                politician.electoral_district
                and politician.electoral_district != existing.electoral_district
            ):
                update_data.electoral_district = politician.electoral_district
                needs_update = True
            if (
                politician.profile_url
                and politician.profile_url != existing.profile_url
            ):
                update_data.profile_url = politician.profile_url
                needs_update = True
            if (
                politician.party_position
                and politician.party_position != existing.party_position
            ):
                update_data.party_position = politician.party_position
                needs_update = True
            if politician.speaker_id and politician.speaker_id != existing.speaker_id:
                update_data.speaker_id = politician.speaker_id
                needs_update = True

            if needs_update:
                self.update_politician(existing.id, update_data)
                logger.info(
                    f"政治家情報を更新しました: {politician.name} (ID: {existing.id})"
                )
                # 更新後のデータを取得
                return self.get_by_id(existing.id)
            else:
                logger.info(
                    f"政治家は既に存在し、更新の必要はありません: "
                    f"{politician.name} (ID: {existing.id})"
                )
                return existing
        else:
            # 新規作成
            politician_id = self.insert_model("politicians", politician, "id")
            if politician_id:
                logger.info(
                    f"新しい政治家を作成しました: {politician.name} "
                    f"(ID: {politician_id})"
                )
                return self.get_by_id(politician_id)
            return None

    def get_by_id(self, politician_id: int) -> Politician | None:
        """IDで政治家を取得"""
        query = "SELECT * FROM politicians WHERE id = :id"
        return self.fetch_as_model(Politician, query, {"id": politician_id})

    def get_by_name_and_party(
        self, name: str, party_id: int | None
    ) -> Politician | None:
        """名前と政党IDで政治家を取得"""
        if party_id is None:
            query = (
                "SELECT * FROM politicians WHERE name = :name "
                "AND political_party_id IS NULL"
            )
            params = {"name": name}
        else:
            query = (
                "SELECT * FROM politicians WHERE name = :name "
                "AND political_party_id = :party_id"
            )
            params = {"name": name, "party_id": party_id}

        return self.fetch_as_model(Politician, query, params)

    def get_all(self) -> list[Politician]:
        """全ての政治家を取得"""
        query = "SELECT * FROM politicians ORDER BY id"
        return self.fetch_all_as_models(Politician, query)

    def get_by_party(self, party_id: int) -> list[Politician]:
        """政党IDで政治家を取得"""
        query = (
            "SELECT * FROM politicians WHERE political_party_id = :party_id "
            "ORDER BY name"
        )
        return self.fetch_all_as_models(Politician, query, {"party_id": party_id})

    def update_politician(
        self, politician_id: int, update_data: PoliticianUpdate
    ) -> bool:
        """政治家情報を更新"""
        rows_affected = self.update_model(
            "politicians", update_data, {"id": politician_id}
        )
        return rows_affected > 0

    def delete_politician(self, politician_id: int) -> bool:
        """政治家を削除"""
        rows_affected = self.delete("politicians", {"id": politician_id})
        return rows_affected > 0

    def search_by_name(self, name_pattern: str) -> list[Politician]:
        """名前パターンで政治家を検索"""
        query = "SELECT * FROM politicians WHERE name LIKE :pattern ORDER BY name"
        return self.fetch_all_as_models(
            Politician, query, {"pattern": f"%{name_pattern}%"}
        )
