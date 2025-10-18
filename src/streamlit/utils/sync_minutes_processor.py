"""同期的な議事録処理実行ユーティリティ"""

import asyncio
from dataclasses import dataclass
from datetime import datetime

from src.application.usecases.execute_minutes_processing_usecase import (
    ExecuteMinutesProcessingDTO,
)
from src.common.logging import get_logger
from src.infrastructure.di.container import get_container, init_container
from src.streamlit.utils.processing_logger import ProcessingLogger

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

    def __init__(self, meeting_id: int, force_reprocess: bool = False):
        """初期化

        Args:
            meeting_id: 処理対象の会議ID
            force_reprocess: 既存データを上書きして再処理するか
        """
        self.meeting_id = meeting_id
        self.force_reprocess = force_reprocess
        self.logger = ProcessingLogger()

    def process(self) -> SyncMinutesProcessingResult:
        """議事録処理を実行する

        Returns:
            処理結果
        """
        start_time = datetime.now()
        errors: list[str] = []

        try:
            self.logger.add_log(self.meeting_id, "処理を開始します", "info")
            self.logger.add_log(
                self.meeting_id,
                f"会議ID {self.meeting_id} の議事録処理を実行します",
                "info",
            )

            # DIコンテナから議事録処理ユースケースを取得
            try:
                container = get_container()
            except RuntimeError:
                # コンテナが初期化されていない場合は初期化
                container = init_container()

            self.logger.add_log(
                self.meeting_id, "議事録処理ユースケースを取得しています...", "info"
            )

            minutes_processing_usecase = (
                container.use_cases.minutes_processing_usecase()
            )

            # リクエストDTOを作成
            request = ExecuteMinutesProcessingDTO(
                meeting_id=self.meeting_id, force_reprocess=self.force_reprocess
            )

            # ユースケースを実行（非同期処理を同期的に実行）
            self.logger.add_log(self.meeting_id, "📝 議事録を処理しています...", "info")

            result = asyncio.run(minutes_processing_usecase.execute(request))

            # 処理完了時間を計算
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            self.logger.add_log(self.meeting_id, "✅ 処理が完了しました", "success")
            self.logger.add_log(
                self.meeting_id,
                f"抽出された発言数: {result.total_conversations}件",
                "info",
            )
            self.logger.add_log(
                self.meeting_id,
                f"抽出された発言者数: {result.unique_speakers}人",
                "info",
            )
            self.logger.add_log(
                self.meeting_id, f"処理時間: {processing_time:.2f}秒", "info"
            )

            return SyncMinutesProcessingResult(
                minutes_id=result.minutes_id,
                meeting_id=result.meeting_id,
                total_conversations=result.total_conversations,
                unique_speakers=result.unique_speakers,
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
            raise
