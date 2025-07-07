"""
Speaker テーブルへのデータ操作を管理するリポジトリクラス
"""

from collections.abc import Sequence

from src.database.typed_repository import TypedRepository
from src.models.speaker_v2 import Speaker


class SpeakerRepository(TypedRepository[Speaker]):
    """Speakerテーブルに対するデータベース操作を管理するクラス"""

    def __init__(self):
        super().__init__(Speaker, "speakers", use_session=True)

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
