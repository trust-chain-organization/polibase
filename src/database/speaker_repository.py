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

    def get_speakers_with_politician_info(self) -> list[dict[str, Any]]:
        """
        政治家情報を含む発言者一覧を取得する

        Returns:
            list[dict]: 発言者と紐付けられた政治家の情報を含む辞書のリスト
        """
        query = """
            SELECT
                s.id,
                s.name,
                s.type,
                s.political_party_name,
                s.position,
                s.is_politician,
                p.id as politician_id,
                p.name as politician_name,
                pp.name as party_name_from_politician,
                COUNT(c.id) as conversation_count
            FROM speakers s
            LEFT JOIN politicians p ON s.id = p.speaker_id
            LEFT JOIN political_parties pp ON p.political_party_id = pp.id
            LEFT JOIN conversations c ON s.id = c.speaker_id
            GROUP BY s.id, s.name, s.type, s.political_party_name,
                     s.position, s.is_politician, p.id, p.name, pp.name
            ORDER BY s.name
        """

        result = self.execute_query(query)
        columns = result.keys()
        rows = result.fetchall()

        return [dict(zip(columns, row, strict=False)) for row in rows]

    def get_speaker_politician_stats(self) -> dict[str, int | float]:
        """
        発言者と政治家の紐付け状況の統計情報を取得する

        Returns:
            dict: 統計情報を含む辞書
        """
        query = """
            WITH stats AS (
                SELECT
                    COUNT(*) as total_speakers,
                    COUNT(CASE WHEN is_politician = TRUE THEN 1 END)
                        as politician_speakers,
                    COUNT(CASE WHEN is_politician = FALSE THEN 1 END)
                        as non_politician_speakers
                FROM speakers
            ),
            linked_stats AS (
                SELECT
                    COUNT(DISTINCT s.id) as linked_speakers
                FROM speakers s
                INNER JOIN politicians p ON s.id = p.speaker_id
                WHERE s.is_politician = TRUE
            )
            SELECT
                stats.total_speakers,
                stats.politician_speakers,
                stats.non_politician_speakers,
                linked_stats.linked_speakers,
                (stats.politician_speakers - linked_stats.linked_speakers)
                    as unlinked_politician_speakers,
                CASE
                    WHEN stats.politician_speakers > 0
                    THEN ROUND(
                        CAST(linked_stats.linked_speakers AS NUMERIC) * 100.0 /
                        stats.politician_speakers, 1
                    )
                    ELSE 0
                END as link_rate
            FROM stats, linked_stats
        """

        result = self.execute_query(query)
        row = result.fetchone()

        if row:
            return {
                "total_speakers": row[0],
                "politician_speakers": row[1],
                "non_politician_speakers": row[2],
                "linked_speakers": row[3],
                "unlinked_politician_speakers": row[4],
                "link_rate": float(row[5]),
            }
        else:
            return {
                "total_speakers": 0,
                "politician_speakers": 0,
                "non_politician_speakers": 0,
                "linked_speakers": 0,
                "unlinked_politician_speakers": 0,
                "link_rate": 0.0,
            }
