"""
Speaker テーブルへのデータ操作を管理するリポジトリクラス
"""

from src.database.base_repository import BaseRepository
from src.politician_extract_processor.models import PoliticianInfo, PoliticianInfoList


class SpeakerRepository(BaseRepository):
    """Speakerテーブルに対するデータベース操作を管理するクラス"""

    def __init__(self):
        super().__init__(use_session=True)

    def save_politician_info_list(
        self, politician_info_list: PoliticianInfoList
    ) -> list[int]:
        """
        PoliticianInfoListをSpeakersテーブルに保存する

        Args:
            politician_info_list: 保存する政治家情報リスト

        Returns:
            List[int]: 保存されたレコードのIDリスト
        """
        saved_ids = []

        try:
            for politician_info in politician_info_list.politician_info_list:
                speaker_id = self._save_speaker(politician_info)
                if speaker_id:
                    saved_ids.append(speaker_id)

            self.session.commit()
            print(f"✅ {len(saved_ids)}件の政治家情報をデータベースに保存しました")
            return saved_ids

        except Exception as e:
            self.session.rollback()
            print(f"❌ データベース保存エラー: {e}")
            raise
        finally:
            self.session.close()

    def _save_speaker(self, politician_info: PoliticianInfo) -> int | None:
        """
        個別のPoliticianInfoをSpeakersテーブルに保存する

        Args:
            politician_info: 保存する政治家情報

        Returns:
            Optional[int]: 保存されたレコードのID（既存の場合はそのID）
        """
        # 既存レコードの確認
        existing_id = self._find_existing_speaker(politician_info)
        if existing_id:
            print(f"🔄 既存レコード発見: {politician_info.name} (ID: {existing_id})")
            return existing_id

        # 新規レコードの挿入
        speaker_id = self.insert(
            table="speakers",
            data={
                "name": politician_info.name,
                "type": "政治家",  # PoliticianInfoなので固定で「政治家」
                "political_party_name": politician_info.party,
                "position": politician_info.position,
                "is_politician": True,
            },
            returning="id",
        )

        print(f"➕ 新規追加: {politician_info.name} (ID: {speaker_id})")
        return speaker_id

    def _find_existing_speaker(self, politician_info: PoliticianInfo) -> int | None:
        """
        既存のSpeakerレコードを検索する

        Args:
            politician_info: 検索する政治家情報

        Returns:
            Optional[int]: 既存レコードのID（存在しない場合はNone）
        """
        query = """
            SELECT id FROM speakers
            WHERE name = :name
            AND (political_party_name = :political_party_name
                OR (political_party_name IS NULL AND :political_party_name IS NULL))
            AND (position = :position OR (position IS NULL AND :position IS NULL))
        """

        row = self.fetch_one(
            query,
            {
                "name": politician_info.name,
                "political_party_name": politician_info.party,
                "position": politician_info.position,
            },
        )

        return row[0] if row else None

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
