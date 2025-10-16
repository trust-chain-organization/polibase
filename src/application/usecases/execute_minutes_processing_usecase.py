"""議事録処理実行ユースケース

議事録一覧画面から発言抽出処理を実行するためのユースケース。
GCSまたはPDFから議事録テキストを取得し、MinutesProcessingServiceを使用して
発言を抽出してデータベースに保存します。
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dtos.minutes_processing_dto import MinutesProcessingResultDTO
from src.application.exceptions import ProcessingError
from src.common.logging import get_logger
from src.domain.entities.conversation import Conversation
from src.domain.entities.meeting import Meeting
from src.domain.entities.minutes import Minutes
from src.domain.entities.speaker import Speaker
from src.domain.repositories.conversation_repository import ConversationRepository
from src.domain.repositories.meeting_repository import MeetingRepository
from src.domain.repositories.minutes_repository import MinutesRepository
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.interfaces.minutes_processing_service import (
    IMinutesProcessingService,
)
from src.domain.services.interfaces.storage_service import IStorageService
from src.domain.services.speaker_domain_service import SpeakerDomainService
from src.domain.value_objects.speaker_speech import SpeakerSpeech

logger = get_logger(__name__)


@dataclass
class ExecuteMinutesProcessingDTO:
    """議事録処理実行リクエストDTO"""

    meeting_id: int
    force_reprocess: bool = False


class ExecuteMinutesProcessingUseCase:
    """議事録処理実行ユースケース

    議事録一覧画面から発言抽出処理を実行するユースケース。
    GCSテキストまたはPDFから議事録を取得し、発言を抽出して保存します。
    """

    def __init__(
        self,
        meeting_repository: MeetingRepository,
        minutes_repository: MinutesRepository,
        conversation_repository: ConversationRepository,
        speaker_repository: SpeakerRepository,
        speaker_domain_service: SpeakerDomainService,
        minutes_processing_service: IMinutesProcessingService,
        storage_service: IStorageService,
        session: AsyncSession,
    ):
        """ユースケースを初期化する

        Args:
            meeting_repository: 会議リポジトリ
            minutes_repository: 議事録リポジトリ
            conversation_repository: 発言リポジトリ
            speaker_repository: 発言者リポジトリ
            speaker_domain_service: 発言者ドメインサービス
            minutes_processing_service: 議事録処理サービス
            storage_service: ストレージサービス
            session: データベースセッション
        """
        self.meeting_repo = meeting_repository
        self.minutes_repo = minutes_repository
        self.conversation_repo = conversation_repository
        self.speaker_repo = speaker_repository
        self.speaker_service = speaker_domain_service
        self.minutes_processing_service = minutes_processing_service
        self.storage_service = storage_service
        self.session = session

        # Ensure all repositories use the same session for transaction consistency
        self.meeting_repo.session = session  # type: ignore[attr-defined]
        self.minutes_repo.session = session  # type: ignore[attr-defined]
        self.conversation_repo.session = session  # type: ignore[attr-defined]
        self.speaker_repo.session = session  # type: ignore[attr-defined]

    async def execute(
        self, request: ExecuteMinutesProcessingDTO
    ) -> MinutesProcessingResultDTO:
        """議事録処理を実行する

        Args:
            request: 処理リクエストDTO

        Returns:
            MinutesProcessingResultDTO: 処理結果

        Raises:
            ValueError: 会議が見つからない、処理可能なソースがない場合
            APIKeyError: APIキーが設定されていない場合
            ProcessingError: 処理中にエラーが発生した場合
        """
        start_time = datetime.now()
        errors: list[str] = []

        try:
            # 会議情報を取得
            meeting = await self.meeting_repo.get_by_id(request.meeting_id)
            if not meeting:
                raise ValueError(f"Meeting {request.meeting_id} not found")

            # 既存の議事録をチェック
            if meeting.id is None:
                raise ValueError("Meeting must have an ID")

            existing_minutes = await self.minutes_repo.get_by_meeting(meeting.id)

            # 強制再処理でない場合、既存のConversationsをチェック
            if existing_minutes and not request.force_reprocess:
                if existing_minutes.id:
                    conversations = await self.conversation_repo.get_by_minutes(
                        existing_minutes.id
                    )
                    if conversations:
                        raise ValueError(
                            f"Meeting {meeting.id} already has conversations"
                        )

            # 議事録テキストを取得
            extracted_text = await self._fetch_minutes_text(meeting)

            # Minutes レコードを作成または取得
            if not existing_minutes:
                minutes = Minutes(
                    meeting_id=meeting.id,
                    url=meeting.url,
                )
                minutes = await self.minutes_repo.create(minutes)
                # Flush to ensure minutes.id is available for foreign key references
                await self.session.flush()
            else:
                minutes = existing_minutes

            # 議事録を処理
            results = await self._process_minutes(extracted_text, meeting.id)

            # Conversationsを保存
            if minutes.id is None:
                raise ValueError("Minutes must have an ID")

            saved_conversations = await self._save_conversations(results, minutes.id)

            # Speakersを抽出・作成
            unique_speakers = await self._extract_and_create_speakers(
                saved_conversations
            )

            # トランザクションをコミット
            await self.session.commit()
            logger.info("Transaction committed successfully")

            # 処理完了時間を計算
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            return MinutesProcessingResultDTO(
                minutes_id=minutes.id if minutes.id is not None else 0,
                meeting_id=meeting.id if meeting.id is not None else 0,
                total_conversations=len(saved_conversations),
                unique_speakers=unique_speakers,
                processing_time_seconds=processing_time,
                processed_at=end_time,
                errors=errors if errors else None,
            )

        except Exception as e:
            errors.append(str(e))
            logger.error(f"Minutes processing failed: {e}", exc_info=True)
            # エラー時はロールバック
            try:
                await self.session.rollback()
                logger.info("Transaction rolled back")
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")
            raise

    async def _fetch_minutes_text(self, meeting: Meeting) -> str:
        """議事録テキストを取得する

        優先順位:
        1. GCSテキストURI
        2. GCS PDF URI

        Args:
            meeting: 会議エンティティ

        Returns:
            str: 議事録テキスト

        Raises:
            ValueError: 処理可能なソースが見つからない場合
        """
        if meeting.gcs_text_uri:
            # GCSからテキストを取得
            try:
                data = await self.storage_service.download_file(meeting.gcs_text_uri)
                if data:
                    text = data.decode("utf-8")
                    logger.info(
                        f"Downloaded text from GCS ({len(text)} characters)",
                        meeting_id=meeting.id,
                    )
                    return text
            except Exception as e:
                logger.warning(f"Failed to download from GCS: {e}")

        # PDFからのテキスト抽出（将来的に実装）
        if meeting.gcs_pdf_uri:
            # TODO: PDF処理の実装
            raise ValueError(
                f"PDF processing not yet implemented for meeting {meeting.id}"
            )

        raise ValueError(f"No valid source found for meeting {meeting.id}")

    async def _process_minutes(self, text: str, meeting_id: int) -> list[SpeakerSpeech]:
        """議事録を処理して発言を抽出する

        Args:
            text: 議事録テキスト
            meeting_id: 会議ID

        Returns:
            list[SpeakerSpeech]: 抽出された発言リスト（ドメイン値オブジェクト）
        """
        if not text:
            raise ProcessingError("No text provided for processing", {"text_length": 0})

        logger.info(f"Processing minutes (text length: {len(text)})")

        # 注入された議事録処理サービスを使用
        results = await self.minutes_processing_service.process_minutes(text)

        logger.info(f"Extracted {len(results)} conversations")
        return results

    async def _save_conversations(
        self, results: list[SpeakerSpeech], minutes_id: int
    ) -> list[Conversation]:
        """発言をデータベースに保存する

        Args:
            results: 抽出された発言データ（ドメイン値オブジェクト）
            minutes_id: 議事録ID

        Returns:
            list[Conversation]: 保存された発言エンティティリスト
        """
        conversations: list[Conversation] = []
        for idx, result in enumerate(results):
            conv = Conversation(
                minutes_id=minutes_id,
                speaker_name=result.speaker,
                comment=result.speech_content,
                sequence_number=idx + 1,
            )
            conversations.append(conv)

        # バルク作成
        saved = await self.conversation_repo.bulk_create(conversations)
        logger.info(
            f"Saved {len(saved)} conversations to database", minutes_id=minutes_id
        )
        return saved

    async def _extract_and_create_speakers(
        self, conversations: list[Conversation]
    ) -> int:
        """発言から一意な発言者を抽出し、発言者レコードを作成する

        Args:
            conversations: 発言エンティティのリスト

        Returns:
            int: 作成された発言者数
        """
        speaker_names: set[tuple[str, str | None]] = set()

        for conv in conversations:
            if conv.speaker_name:
                # 名前から政党情報を抽出
                clean_name, party_info = self.speaker_service.extract_party_from_name(
                    conv.speaker_name
                )
                speaker_names.add((clean_name, party_info))

        # 発言者レコードを作成
        created_count = 0
        for name, party_info in speaker_names:
            # 既存の発言者をチェック
            existing = await self.speaker_repo.get_by_name_party_position(
                name, party_info, None
            )

            if not existing:
                # 新規発言者を作成
                speaker = Speaker(
                    name=name,
                    political_party_name=party_info,
                    is_politician=bool(party_info),  # 政党があれば政治家と仮定
                )
                await self.speaker_repo.create(speaker)
                created_count += 1

        logger.info(f"Created {created_count} new speakers")
        return created_count
