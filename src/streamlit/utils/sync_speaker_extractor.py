"""同期的な発言者抽出処理

このモジュールは、Streamlitから呼び出される同期的な発言者抽出処理を提供します。
既存のConversationsから発言者を抽出し、Speakerレコードを作成します。
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.domain.entities.speaker import Speaker
from src.domain.services.speaker_domain_service import SpeakerDomainService
from src.infrastructure.persistence.conversation_repository_impl import (
    ConversationRepositoryImpl as AsyncConversationRepo,
)
from src.infrastructure.persistence.minutes_repository_impl import (
    MinutesRepositoryImpl as AsyncMinutesRepo,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.infrastructure.persistence.speaker_repository_impl import (
    SpeakerRepositoryImpl as AsyncSpeakerRepo,
)
from src.streamlit.utils.processing_logger import ProcessingLogger

logger = logging.getLogger(__name__)


@dataclass
class SyncSpeakerExtractionResult:
    """同期発言者抽出処理の結果"""

    meeting_id: int
    total_conversations: int
    unique_speakers: int
    new_speakers: int
    existing_speakers: int
    processing_time_seconds: float
    processed_at: datetime
    errors: list[str] | None = None


class SyncSpeakerExtractor:
    """同期的に発言者抽出処理を実行するクラス"""

    def __init__(self, meeting_id: int):
        """初期化

        Args:
            meeting_id: 処理対象の会議ID
        """
        self.meeting_id = meeting_id
        self.logger = ProcessingLogger()

    def process(self) -> SyncSpeakerExtractionResult:
        """発言者抽出処理を実行する

        Returns:
            処理結果
        """
        start_time = datetime.now()
        errors: list[str] = []

        try:
            self.logger.add_log(self.meeting_id, "処理を開始します", "info")
            self.logger.add_log(
                self.meeting_id,
                f"会議ID {self.meeting_id} の発言者抽出処理を実行します",
                "info",
            )

            # 同期リポジトリを使用
            self.logger.add_log(
                self.meeting_id, "データベースに接続しています...", "info"
            )
            minutes_repo = RepositoryAdapter(AsyncMinutesRepo)
            conversation_repo = RepositoryAdapter(AsyncConversationRepo)
            speaker_repo = RepositoryAdapter(AsyncSpeakerRepo)

            # ドメインサービスを初期化
            speaker_service = SpeakerDomainService()

            self.logger.add_log(
                self.meeting_id, "議事録情報を取得しています...", "info"
            )

            # 議事録を取得
            minutes = minutes_repo.get_by_meeting(self.meeting_id)
            if not minutes or not minutes.id:
                raise ValueError(f"No minutes found for meeting {self.meeting_id}")

            # Conversationsを取得
            conversations = conversation_repo.get_by_minutes(minutes.id)
            if not conversations:
                raise ValueError(
                    f"No conversations found for meeting {self.meeting_id}"
                )

            self.logger.add_log(
                self.meeting_id,
                f"📝 {len(conversations)}件の発言を取得しました",
                "info",
            )

            # 既存のSpeakers数をカウント
            conversations_with_speakers = [
                c for c in conversations if c.speaker_id is not None
            ]
            if conversations_with_speakers:
                raise ValueError(
                    f"Meeting {self.meeting_id} already has "
                    f"{len(conversations_with_speakers)} "
                    f"conversations with speakers linked"
                )

            # 発言者を抽出・作成
            self.logger.add_log(self.meeting_id, "発言者を抽出しています...", "info")
            extraction_result = self._extract_and_create_speakers(
                conversations, speaker_repo, speaker_service
            )

            # 結果をログに記録
            self.logger.add_log(
                self.meeting_id,
                f"🔍 {len(conversations)}件の発言から"
                f"{extraction_result['unique_speakers']}人の発言者を検出しました",
                "info",
            )
            self.logger.add_log(
                self.meeting_id,
                f"✅ 新規作成: {extraction_result['new_speakers']}人、"
                f"既存: {extraction_result['existing_speakers']}人",
                "info",
            )

            # 処理完了時間を計算
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            self.logger.add_log(self.meeting_id, "✅ 処理が完了しました", "success")
            self.logger.add_log(
                self.meeting_id, f"処理時間: {processing_time:.2f}秒", "info"
            )

            # リポジトリを閉じる
            minutes_repo.close()
            conversation_repo.close()
            speaker_repo.close()

            return SyncSpeakerExtractionResult(
                meeting_id=self.meeting_id,
                total_conversations=len(conversations),
                unique_speakers=extraction_result["unique_speakers"],
                new_speakers=extraction_result["new_speakers"],
                existing_speakers=extraction_result["existing_speakers"],
                processing_time_seconds=processing_time,
                processed_at=end_time,
                errors=errors if errors else None,
            )

        except Exception as e:
            error_msg = str(e)
            self.logger.add_log(
                self.meeting_id, f"❌ エラーが発生しました: {error_msg}", "error"
            )
            logger.error(
                f"Processing failed for meeting {self.meeting_id}: {e}", exc_info=True
            )

            # エラーでも結果を返す
            return SyncSpeakerExtractionResult(
                meeting_id=self.meeting_id,
                total_conversations=0,
                unique_speakers=0,
                new_speakers=0,
                existing_speakers=0,
                processing_time_seconds=(datetime.now() - start_time).total_seconds(),
                processed_at=datetime.now(),
                errors=[error_msg],
            )

    def _extract_and_create_speakers(
        self, conversations: list[Any], speaker_repo: Any, speaker_service: Any
    ) -> dict[str, int]:
        """発言から一意な発言者を抽出し、発言者レコードを作成する

        Args:
            conversations: 発言エンティティのリスト
            speaker_repo: 発言者リポジトリ
            speaker_service: 発言者ドメインサービス

        Returns:
            dict: 抽出結果の統計情報
                - unique_speakers: ユニークな発言者数
                - new_speakers: 新規作成された発言者数
                - existing_speakers: 既存の発言者数
        """
        speaker_names: set[tuple[str, str | None]] = set()

        # 全conversationsから発言者名を抽出
        for conv in conversations:
            if conv.speaker_name:
                # 名前から政党情報を抽出
                clean_name, party_info = speaker_service.extract_party_from_name(
                    conv.speaker_name
                )
                speaker_names.add((clean_name, party_info))

        logger.info(f"Found {len(speaker_names)} unique speaker names")

        # 発言者レコードを作成
        new_speakers = 0
        existing_speakers = 0

        for name, party_info in speaker_names:
            # 既存の発言者をチェック
            existing = speaker_repo.get_by_name_party_position(name, party_info, None)

            if not existing:
                # 新規発言者を作成
                speaker = Speaker(
                    name=name,
                    political_party_name=party_info,
                    is_politician=bool(party_info),  # 政党があれば政治家と仮定
                )
                speaker_repo.create(speaker)
                new_speakers += 1
                logger.debug(f"Created new speaker: {name}")
            else:
                existing_speakers += 1
                logger.debug(f"Speaker already exists: {name}")

        logger.info(
            f"Speaker extraction complete - "
            f"New: {new_speakers}, Existing: {existing_speakers}"
        )

        return {
            "unique_speakers": len(speaker_names),
            "new_speakers": new_speakers,
            "existing_speakers": existing_speakers,
        }
