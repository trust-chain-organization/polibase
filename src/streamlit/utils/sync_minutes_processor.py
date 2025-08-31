"""同期的な議事録処理実行ユーティリティ"""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.common.logging import get_logger
from src.domain.entities.conversation import Conversation
from src.domain.entities.minutes import Minutes
from src.domain.entities.speaker import Speaker
from src.exceptions import APIKeyError, ProcessingError
from src.infrastructure.external.llm_service_factory import LLMServiceFactory
from src.infrastructure.persistence.conversation_repository_impl import (
    ConversationRepositoryImpl as AsyncConversationRepo,
)
from src.infrastructure.persistence.meeting_repository_impl import (
    MeetingRepositoryImpl as AsyncMeetingRepo,
)
from src.infrastructure.persistence.minutes_repository_impl import (
    MinutesRepositoryImpl as AsyncMinutesRepo,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.infrastructure.persistence.speaker_repository_impl import (
    SpeakerRepositoryImpl as AsyncSpeakerRepo,
)
from src.minutes_divide_processor.minutes_process_agent import MinutesProcessAgent
from src.streamlit.utils.processing_logger import ProcessingLogger
from src.utils.gcs_storage import GCSStorage

logger = get_logger(__name__)


@dataclass
class SyncMinutesProcessingResult:
    """同期処理結果"""

    minutes_id: int
    meeting_id: int
    total_conversations: int
    unique_speakers: int
    processing_time_seconds: float
    processed_at: datetime
    errors: list[str] | None = None


class SyncMinutesProcessor:
    """同期的に議事録処理を実行するクラス"""

    def __init__(self, meeting_id: int):
        """初期化

        Args:
            meeting_id: 処理対象の会議ID
        """
        self.meeting_id = meeting_id
        self.logger = ProcessingLogger()

    def process(self) -> SyncMinutesProcessingResult:
        """議事録処理を実行する

        Returns:
            処理結果
        """
        start_time = datetime.now()
        errors = []

        try:
            self.logger.add_log(self.meeting_id, "処理を開始します", "info")
            self.logger.add_log(
                self.meeting_id,
                f"会議ID {self.meeting_id} の議事録処理を実行します",
                "info",
            )

            # 同期リポジトリを使用
            self.logger.add_log(
                self.meeting_id, "データベースに接続しています...", "info"
            )
            meeting_repo = RepositoryAdapter(AsyncMeetingRepo)
            minutes_repo = RepositoryAdapter(AsyncMinutesRepo)
            conversation_repo = RepositoryAdapter(AsyncConversationRepo)
            speaker_repo = RepositoryAdapter(AsyncSpeakerRepo)

            self.logger.add_log(self.meeting_id, "会議情報を取得しています...", "info")
            # 会議情報を取得
            meeting = meeting_repo.get_by_id(self.meeting_id)
            if not meeting:
                raise ValueError(f"Meeting {self.meeting_id} not found")

            # 既存の議事録をチェック
            existing_minutes = minutes_repo.get_by_meeting(self.meeting_id)

            # 既存のConversationsをチェック
            if existing_minutes and existing_minutes.id:
                conversations = conversation_repo.get_by_minutes(existing_minutes.id)
                if conversations:
                    raise ValueError(
                        f"Meeting {self.meeting_id} already has conversations"
                    )

            # 議事録テキストを取得
            self.logger.add_log(
                self.meeting_id, "議事録テキストを取得しています...", "info"
            )
            extracted_text = self._fetch_minutes_text(meeting)

            # 取得したテキストの概要をログに記録
            text_length = len(extracted_text)
            preview_length = min(500, text_length)  # 最初の500文字まで表示
            text_preview = extracted_text[:preview_length]
            if text_length > preview_length:
                text_preview += f"\n\n... (全{text_length:,}文字)"

            self.logger.add_log(
                self.meeting_id,
                f"📄 議事録テキストを取得しました（{text_length:,}文字）",
                "info",
                details=text_preview,
            )

            # Minutes レコードを作成または取得
            if not existing_minutes:
                minutes = Minutes(
                    meeting_id=self.meeting_id,
                    url=meeting.url,
                )
                minutes = minutes_repo.create(minutes)
            else:
                minutes = existing_minutes

            # 議事録を処理
            self.logger.add_log(self.meeting_id, "議事録を処理しています...", "info")
            results = self._process_minutes(extracted_text)

            # 抽出結果のサマリーをログに記録
            if results:
                result_summary = []
                for i, result in enumerate(results[:5], 1):  # 最初の5件を表示
                    speaker = getattr(result, "speaker", "不明")
                    content = getattr(result, "speech_content", "")
                    preview = content[:100] + "..." if len(content) > 100 else content
                    result_summary.append(f"{i}. {speaker}: {preview}")

                if len(results) > 5:
                    result_summary.append(f"\n... 他{len(results) - 5}件の発言")

                self.logger.add_log(
                    self.meeting_id,
                    f"📝 {len(results)}件の発言を抽出しました",
                    "info",
                    details="\n".join(result_summary),
                )

            # Conversationsを保存
            self.logger.add_log(self.meeting_id, "発言を保存しています...", "info")
            saved_conversations = self._save_conversations(
                results, minutes.id, conversation_repo
            )

            # Speakersを抽出・作成
            self.logger.add_log(self.meeting_id, "発言者を抽出しています...", "info")
            unique_speakers = self._extract_and_create_speakers(
                saved_conversations, speaker_repo
            )

            # 処理完了時間を計算
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            self.logger.add_log(self.meeting_id, "✅ 処理が完了しました", "success")
            self.logger.add_log(
                self.meeting_id,
                f"抽出された発言数: {len(saved_conversations)}件",
                "info",
            )
            self.logger.add_log(
                self.meeting_id, f"抽出された発言者数: {unique_speakers}人", "info"
            )
            self.logger.add_log(
                self.meeting_id, f"処理時間: {processing_time:.2f}秒", "info"
            )

            # リポジトリを閉じる
            meeting_repo.close()
            minutes_repo.close()
            conversation_repo.close()
            speaker_repo.close()

            return SyncMinutesProcessingResult(
                minutes_id=minutes.id if minutes.id else 0,
                meeting_id=self.meeting_id,
                total_conversations=len(saved_conversations),
                unique_speakers=unique_speakers,
                processing_time_seconds=processing_time,
                processed_at=end_time,
                errors=errors if errors else None,
            )

        except Exception as e:
            self.logger.add_log(
                self.meeting_id, f"❌ エラーが発生しました: {str(e)}", "error"
            )
            logger.error(
                f"Processing failed for meeting {self.meeting_id}: {e}", exc_info=True
            )
            raise

    def _fetch_minutes_text(self, meeting: Any) -> str:
        """議事録テキストを取得する"""
        if meeting.gcs_text_uri:
            try:
                from src.config import config

                gcs_storage = GCSStorage(
                    bucket_name=config.GCS_BUCKET_NAME,
                    project_id=config.GCS_PROJECT_ID,
                )
                text = gcs_storage.download_content(meeting.gcs_text_uri)
                if text:
                    logger.info(
                        f"Downloaded text from GCS ({len(text)} characters)",
                        meeting_id=meeting.id,
                    )
                    return text
            except Exception as e:
                logger.warning(f"Failed to download from GCS: {e}")

        if meeting.gcs_pdf_uri:
            raise ValueError(
                f"PDF processing not yet implemented for meeting {meeting.id}"
            )

        raise ValueError(f"No valid source found for meeting {meeting.id}")

    def _process_minutes(self, text: str) -> list[Any]:
        """議事録を処理して発言を抽出する"""
        if not text:
            raise ProcessingError("No text provided for processing", {"text_length": 0})

        # APIキーをチェック
        if not os.getenv("GOOGLE_API_KEY"):
            raise APIKeyError(
                "GOOGLE_API_KEY not set. Please configure it in your .env file",
                {"env_var": "GOOGLE_API_KEY"},
            )

        # LLMサービスを作成
        llm_service = LLMServiceFactory.create_gemini_service(temperature=0.0)

        # MinutesProcessAgentを使用して処理
        agent = MinutesProcessAgent(llm_service=llm_service)

        logger.info(f"Processing minutes (text length: {len(text)})")

        # 同期的に実行
        results = agent.run(text)

        logger.info(f"Extracted {len(results)} conversations")
        return results

    def _save_conversations(
        self, results: list[Any], minutes_id: int, repo: Any
    ) -> list[Conversation]:
        """発言をデータベースに保存する"""
        conversations = []
        for idx, result in enumerate(results):
            conv = Conversation(
                minutes_id=minutes_id,
                speaker_name=result.speaker,
                comment=result.speech_content,
                sequence_number=idx + 1,
            )
            conversations.append(conv)

        # バルク作成
        saved = repo.bulk_create(conversations)
        logger.info(
            f"Saved {len(saved)} conversations to database", minutes_id=minutes_id
        )
        return saved

    def _extract_and_create_speakers(
        self, conversations: list[Conversation], speaker_repo: Any
    ) -> int:
        """発言から一意な発言者を抽出し、発言者レコードを作成する"""
        from src.domain.services.speaker_domain_service import SpeakerDomainService

        speaker_service = SpeakerDomainService()
        speaker_names = set()

        for conv in conversations:
            if conv.speaker_name:
                clean_name, party_info = speaker_service.extract_party_from_name(
                    conv.speaker_name
                )
                speaker_names.add((clean_name, party_info))

        # 発言者レコードを作成
        created_count = 0
        for name, party_info in speaker_names:
            # 既存の発言者をチェック
            existing = speaker_repo.get_by_name_party_position(name, party_info, None)

            if not existing:
                # 新規発言者を作成
                speaker = Speaker(
                    name=name,
                    political_party_name=party_info,
                    is_politician=bool(party_info),
                )
                speaker_repo.create(speaker)
                created_count += 1

        logger.info(f"Created {created_count} new speakers")
        return created_count
