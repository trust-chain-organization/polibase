"""同期的な発言者抽出処理

このモジュールは、Streamlitから呼び出される同期的な発言者抽出処理を提供します。
既存のConversationsから発言者を抽出し、Speakerレコードを作成します。
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from src.application.usecases.execute_speaker_extraction_usecase import (
    ExecuteSpeakerExtractionDTO,
)
from src.infrastructure.di.container import get_container, init_container
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

    def __init__(self, meeting_id: int, force_reprocess: bool = False):
        """初期化

        Args:
            meeting_id: 処理対象の会議ID
            force_reprocess: 既存データを上書きして再処理するか
        """
        self.meeting_id = meeting_id
        self.force_reprocess = force_reprocess
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

            # DIコンテナから発言者抽出ユースケースを取得
            try:
                container = get_container()
            except RuntimeError:
                # コンテナが初期化されていない場合は初期化
                container = init_container()

            self.logger.add_log(
                self.meeting_id, "発言者抽出ユースケースを取得しています...", "info"
            )

            speaker_extraction_usecase = (
                container.use_cases.speaker_extraction_usecase()
            )

            # リクエストDTOを作成
            request = ExecuteSpeakerExtractionDTO(
                meeting_id=self.meeting_id, force_reprocess=self.force_reprocess
            )

            # ユースケースを実行（非同期処理を同期的に実行）
            self.logger.add_log(self.meeting_id, "🎤 発言者を抽出しています...", "info")

            result = asyncio.run(speaker_extraction_usecase.execute(request))

            # 処理完了時間を計算
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            self.logger.add_log(self.meeting_id, "✅ 処理が完了しました", "success")
            self.logger.add_log(
                self.meeting_id,
                f"✅ 新規作成: {result.new_speakers}人、"
                f"既存: {result.existing_speakers}人",
                "info",
            )
            self.logger.add_log(
                self.meeting_id, f"処理時間: {processing_time:.2f}秒", "info"
            )

            return SyncSpeakerExtractionResult(
                meeting_id=result.meeting_id,
                total_conversations=result.total_conversations,
                unique_speakers=result.unique_speakers,
                new_speakers=result.new_speakers,
                existing_speakers=result.existing_speakers,
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
