"""
Speaker テーブルへのデータ操作を管理するリポジトリクラス
"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy.orm import Session

from src.database.typed_repository import TypedRepository
from src.models.speaker_v2 import Speaker


class SpeakerRepository(TypedRepository[Speaker]):
    """Speakerテーブルに対するデータベース操作を管理するクラス"""

    def __init__(self, session: Session | None = None):
        super().__init__(Speaker, "speakers", use_session=True, session=session)

    # Removed save_politician_info_list and related methods
    # These were used for extracting politicians from minutes which is now disabled

    def get_all_speakers(self) -> Sequence[Speaker]:
        """
        全てのSpeakerレコードを取得する

        Returns:
            Sequence[Speaker]: Speakerレコードのリスト
        """
        query = """
            SELECT id, name, type, political_party_name, position,
                is_politician, created_at, updated_at
            FROM speakers
            ORDER BY created_at DESC
        """

        return self.fetch_all(query)

    def get_all_speakers_with_conversation_count(
        self, offset: int = 0, limit: int = 20
    ) -> tuple[Sequence[dict[str, Any]], int]:
        """
        発言者一覧を発言数付きで取得する

        Args:
            offset: 取得開始位置
            limit: 取得件数

        Returns:
            tuple[Sequence[dict], int]: (発言者データのリスト, 総件数)
        """
        # 総件数を取得
        count_query = "SELECT COUNT(*) as total FROM speakers"
        count_result = self.execute_query(count_query)
        count_row = count_result.fetchone()
        total_count = count_row[0] if count_row else 0

        # 発言者と発言数を取得
        query = """
            SELECT
                s.id,
                s.name,
                s.type,
                s.political_party_name,
                s.position,
                s.is_politician,
                COALESCE(COUNT(c.id), 0) as conversation_count
            FROM speakers s
            LEFT JOIN conversations c ON s.id = c.speaker_id
            GROUP BY s.id, s.name, s.type, s.political_party_name,
                     s.position, s.is_politician
            ORDER BY s.name
            LIMIT :limit OFFSET :offset
        """

        result = self.execute_query(query, {"limit": limit, "offset": offset})
        columns = result.keys()
        rows = [dict(zip(columns, row, strict=False)) for row in result.fetchall()]

        return rows, total_count

    def get_speakers_count(self) -> int:
        """
        Speakersテーブルのレコード数を取得する

        Returns:
            int: レコード数
        """
        return self.count()

    def find_by_name(self, name: str) -> Speaker | None:
        """
        名前で発言者を検索する

        Args:
            name: 発言者名

        Returns:
            Speaker: 発言者情報（見つからない場合はNone）
        """
        query = """
            SELECT id, name, type, political_party_name, position,
                is_politician, created_at, updated_at
            FROM speakers
            WHERE name = :name
            LIMIT 1
        """
        return self.fetch_one(query, {"name": name})

    def get_speakers_not_linked_to_politicians(self) -> Sequence[Speaker]:
        """
        is_politician=Falseの発言者を取得する

        Returns:
            Sequence[Speaker]: 政治家でない発言者のリスト
        """
        query = """
            SELECT id, name, type, political_party_name, position,
                is_politician, created_at, updated_at
            FROM speakers
            WHERE is_politician = FALSE
            ORDER BY name
        """
        return self.fetch_all(query)
