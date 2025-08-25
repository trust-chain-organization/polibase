"""Use case for processing meeting minutes."""

from datetime import datetime
from typing import Any

from src.application.dtos.minutes_dto import (
    ExtractedSpeechDTO,
    MinutesProcessingResultDTO,
    ProcessMinutesDTO,
)
from src.domain.entities.conversation import Conversation
from src.domain.entities.meeting import Meeting
from src.domain.entities.minutes import Minutes
from src.domain.services.minutes_domain_service import MinutesDomainService
from src.domain.services.speaker_domain_service import SpeakerDomainService


class ProcessMinutesUseCase:
    """議事録処理ユースケース

    議事録PDFまたはテキストを処理し、発言を抽出して
    データベースに保存します。

    Attributes:
        meeting_repo: 会議リポジトリ
        minutes_repo: 議事録リポジトリ
        conversation_repo: 発言リポジトリ
        speaker_repo: 発言者リポジトリ
        minutes_service: 議事録ドメインサービス
        speaker_service: 発言者ドメインサービス
        pdf_processor: PDF処理サービス
        text_extractor: テキスト抽出サービス

    Example:
        >>> use_case = ProcessMinutesUseCase(
        ...     meeting_repo, minutes_repo, conversation_repo,
        ...     speaker_repo, minutes_service, speaker_service,
        ...     pdf_processor, text_extractor
        ... )
        >>> result = use_case.execute(ProcessMinutesDTO(meeting_id=123))
        >>> print(f"処理された発言数: {result.total_conversations}")
    """

    def __init__(
        self,
        meeting_repository: Any,
        minutes_repository: Any,
        conversation_repository: Any,
        speaker_repository: Any,
        minutes_domain_service: MinutesDomainService,
        speaker_domain_service: SpeakerDomainService,
        pdf_processor: Any,  # Mock service for now
        text_extractor: Any,  # Mock service for now
    ):
        """議事録処理ユースケースを初期化する

        Args:
            meeting_repository: 会議リポジトリの実装
            minutes_repository: 議事録リポジトリの実装
            conversation_repository: 発言リポジトリの実装
            speaker_repository: 発言者リポジトリの実装
            minutes_domain_service: 議事録ドメインサービス
            speaker_domain_service: 発言者ドメインサービス
            pdf_processor: PDF処理サービス
            text_extractor: テキスト抽出サービス
        """
        self.meeting_repo = meeting_repository
        self.minutes_repo = minutes_repository
        self.conversation_repo = conversation_repository
        self.speaker_repo = speaker_repository
        self.minutes_service = minutes_domain_service
        self.speaker_service = speaker_domain_service
        self.pdf_processor = pdf_processor
        self.text_extractor = text_extractor

    def execute(self, request: ProcessMinutesDTO) -> MinutesProcessingResultDTO:
        """議事録を処理する

        以下の手順で議事録を処理します：
        1. 会議情報の取得
        2. 既存処理のチェック
        3. PDFまたはテキストからの発言抽出
        4. 発言データの保存
        5. 発言者情報の抽出と作成

        Args:
            request: 処理リクエストDTO
                - meeting_id: 処理対象の会議ID
                - force_reprocess: 既存データを強制的に再処理するか
                - pdf_url: PDFのURL（オプション）
                - gcs_text_uri: GCSテキストURI（オプション）

        Returns:
            MinutesProcessingResultDTO: 処理結果
                - minutes_id: 議事録ID
                - meeting_id: 会議ID
                - total_conversations: 抽出された発言数
                - unique_speakers: 作成された発言者数
                - processing_time_seconds: 処理時間（秒）
                - processed_at: 処理完了日時
                - errors: エラーメッセージリスト（エラー時のみ）

        Raises:
            ValueError: 会議が見つからない、処理可能なソースがない場合
            Exception: 処理中にエラーが発生した場合
        """
        start_time = datetime.now()
        errors: list[str] = []

        # Get meeting
        meeting = self.meeting_repo.get_by_id(request.meeting_id)
        if not meeting:
            raise ValueError(f"Meeting {request.meeting_id} not found")

        # Check if minutes already exist
        if meeting.id is None:
            raise ValueError("Meeting must have an ID")
        existing_minutes = self.minutes_repo.get_by_meeting(meeting.id)
        if existing_minutes and not request.force_reprocess:
            if self.minutes_service.is_minutes_processed(existing_minutes):
                raise ValueError(f"Minutes for meeting {meeting.id} already processed")

        # Create or get minutes record
        if not existing_minutes:
            if meeting.id is None:
                raise ValueError("Meeting must have an ID")
            minutes = Minutes(
                meeting_id=meeting.id,
                url=request.pdf_url or meeting.url,
            )
            minutes = self.minutes_repo.create(minutes)
        else:
            minutes = existing_minutes

        try:
            # Extract speeches from minutes
            speeches = self._extract_speeches(
                meeting, request.pdf_url, request.gcs_text_uri
            )

            # Create conversations from speeches
            if minutes.id is None:
                raise ValueError("Minutes must have an ID")
            conversations = self.minutes_service.create_conversations_from_speeches(
                speeches, minutes.id
            )

            # Save conversations
            saved_conversations = self.conversation_repo.bulk_create(conversations)

            # Extract and create speakers
            unique_speakers = self._extract_and_create_speakers(saved_conversations)

            # Mark minutes as processed
            if minutes.id is None:
                raise ValueError("Minutes must have an ID")
            self.minutes_repo.mark_processed(minutes.id)
            # Calculate processing time
            end_time = datetime.now()
            processing_time = self.minutes_service.calculate_processing_duration(
                start_time, end_time
            )

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
            raise

    def _extract_speeches(
        self,
        meeting: Meeting,
        pdf_url: str | None,
        gcs_text_uri: str | None,
    ) -> list[ExtractedSpeechDTO]:
        """議事録ソースから発言を抽出する

        優先順位：
        1. GCSテキストURI
        2. PDFのURL
        3. 会議のGCS PDF URI

        Args:
            meeting: 会議エンティティ
            pdf_url: PDFのURL（オプション）
            gcs_text_uri: GCSテキストURI（オプション）

        Returns:
            ExtractedSpeechDTO のリスト

        Raises:
            ValueError: 処理可能なソースが見つからない場合
        """
        if gcs_text_uri:
            # Extract from GCS text
            text_content = self.text_extractor.extract_from_gcs(gcs_text_uri)
            speeches = self.text_extractor.parse_speeches(text_content)
        elif pdf_url or meeting.gcs_pdf_uri:
            # Extract from PDF
            url = pdf_url or meeting.gcs_pdf_uri
            if url is None:
                raise ValueError("No PDF URL available")
            speeches = self.pdf_processor.process_pdf(url)
        else:
            raise ValueError("No valid source for minutes processing")

        # Convert to DTOs
        return [
            ExtractedSpeechDTO(
                speaker_name=s.get("speaker", ""),
                content=s.get("content", ""),
                sequence_number=idx + 1,
            )
            for idx, s in enumerate(speeches)
        ]

    def _extract_and_create_speakers(self, conversations: list[Conversation]) -> int:
        """発言から一意な発言者を抽出し、発言者レコードを作成する

        Args:
            conversations: 発言エンティティのリスト

        Returns:
            作成された発言者数
        """
        speaker_names: set[tuple[str, str | None]] = set()

        for conv in conversations:
            if conv.speaker_name:
                # Extract clean name and party info
                clean_name, party_info = self.speaker_service.extract_party_from_name(
                    conv.speaker_name
                )
                speaker_names.add((clean_name, party_info))

        # Create speaker records
        created_count = 0
        for name, party_info in speaker_names:
            # Check if speaker exists
            existing = self.speaker_repo.get_by_name_party_position(
                name, party_info, None
            )

            if not existing:
                # Create new speaker
                from src.domain.entities.speaker import Speaker

                speaker = Speaker(
                    name=name,
                    political_party_name=party_info,
                    is_politician=bool(party_info),  # Assume politician if has party
                )
                self.speaker_repo.create(speaker)
                created_count += 1

        return created_count
