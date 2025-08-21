"""Extract speakers command."""

from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.database import DATABASE_URL
from src.extract_speakers_from_minutes import SpeakerExtractorFromMinutes
from src.interfaces.cli.base import BaseCommand, Command, with_error_handling


class ExtractSpeakersCommand(Command, BaseCommand):
    """Command to extract speakers from minutes and link to politicians."""

    @with_error_handling
    def execute(self, **kwargs: Any) -> None:
        """Extract speakers from minutes and link to politicians.

        議事録から発言者を抽出してspeaker/politicianと紐付けます。
        """
        minutes_id = kwargs.get("minutes_id")
        use_llm = kwargs.get("use_llm", False)
        skip_extraction = kwargs.get("skip_extraction", False)
        skip_politician_link = kwargs.get("skip_politician_link", False)
        skip_conversation_link = kwargs.get("skip_conversation_link", False)

        self.show_progress("議事録から発言者を抽出してspeaker/politicianと紐付けます")

        # データベース接続
        engine = create_engine(DATABASE_URL)
        session_local = sessionmaker(bind=engine)

        with session_local() as session:
            extractor = SpeakerExtractorFromMinutes(session)

            try:
                # 1. 発言者抽出
                if not skip_extraction:
                    self.show_progress("発言者抽出を開始...")
                    extractor.extract_speakers_from_minutes(minutes_id)
                    self.success("発言者抽出が完了しました")

                # 2. speaker-politician紐付け
                if not skip_politician_link:
                    self.show_progress("speaker-politician紐付けを開始...")
                    extractor.link_speakers_to_politicians(use_llm=use_llm)
                    self.success("speaker-politician紐付けが完了しました")

                # 3. conversation-speaker紐付け
                if not skip_conversation_link:
                    self.show_progress("conversation-speaker紐付けを開始...")
                    extractor.update_conversation_speaker_links(use_llm=use_llm)
                    self.success("conversation-speaker紐付けが完了しました")

                self.success("全処理が完了しました！")

            except Exception as e:
                self.error(f"エラー: {e}")
                session.rollback()
                raise
