"""
Speaker テーブルへのデータ操作を管理するリポジトリクラス
"""

from src.database.base_repository import BaseRepository


class SpeakerRepository(BaseRepository):
    """Speakerテーブルに対するデータベース操作を管理するクラス"""

    def __init__(self):
        super().__init__(use_session=True)

    # Removed save_politician_info_list and related methods
    # These were used for extracting politicians from minutes which is now disabled

    def get_all_speakers(self) -> list[dict]:
        """
        全てのSpeakerレコードを取得する

        Returns:
            List[dict]: Speakerレコードのリスト
        """
        query = """
            SELECT id, name, type, political_party_name, position,
                is_politician, created_at, updated_at
            FROM speakers
            ORDER BY created_at DESC
        """

        return self.fetch_as_dict(query)

    def get_speakers_count(self) -> int:
        """
        Speakersテーブルのレコード数を取得する

        Returns:
            int: レコード数
        """
        return self.count("speakers")

    def find_by_name(self, name: str) -> dict | None:
        """
        名前で発言者を検索する

        Args:
            name: 発言者名

        Returns:
            dict: 発言者情報（見つからない場合はNone）
        """
        query = """
            SELECT id, name, type, political_party_name, position,
                is_politician, created_at, updated_at
            FROM speakers
            WHERE name = :name
            LIMIT 1
        """
        speakers = self.fetch_as_dict(query, {"name": name})
        return speakers[0] if speakers else None

    def get_speakers_not_linked_to_politicians(self) -> list[dict]:
        """
        is_politician=Falseの発言者を取得する

        Returns:
            List[dict]: 政治家でない発言者のリスト
        """
        query = """
            SELECT id, name, type, political_party_name, position,
                is_politician, created_at, updated_at
            FROM speakers
            WHERE is_politician = FALSE
            ORDER BY name
        """
        return self.fetch_as_dict(query)
