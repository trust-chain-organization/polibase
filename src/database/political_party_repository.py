"""Repository for managing political party data"""

import logging

from sqlalchemy.orm import Session

from src.database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class PoliticalPartyRepository(BaseRepository):
    """Repository for managing political party data"""

    def __init__(self, session: Session | None = None):
        if session:
            super().__init__(use_session=True)
            self._session = session
        else:
            super().__init__(use_session=False)

    def create_party_if_not_exists(self, party_name: str) -> int | None:
        """政党が存在しない場合のみ作成"""
        with self.transaction():
            # 既存の政党をチェック
            existing = self.get_by_name(party_name)
            if existing:
                return existing[0]  # Return existing ID

            # 新規作成
            party_id = self.insert("political_parties", {"name": party_name}, "id")
            if party_id:
                logger.info(f"新しい政党を作成しました: {party_name} (ID: {party_id})")
            return party_id

    def get_by_name(self, name: str) -> tuple[int, str] | None:
        """名前で政党を取得"""
        query = "SELECT id, name FROM political_parties WHERE name = :name"
        return self.fetch_one(query, {"name": name})

    def get_all(self) -> list[tuple[int, str]]:
        """全ての政党を取得"""
        query = "SELECT id, name FROM political_parties ORDER BY id"
        return self.fetch_all(query)
