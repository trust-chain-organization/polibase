"""同期的に政治家抽出処理を実行するユーティリティ"""

import logging
from dataclasses import dataclass
from datetime import datetime

from src.application.dtos.politician_dto import ScrapePoliticiansInputDTO
from src.infrastructure.di.container import init_container
from src.streamlit.utils.processing_logger import ProcessingLogger

logger = logging.getLogger(__name__)


@dataclass
class SyncPoliticianScrapingResult:
    """政治家抽出処理の結果"""

    party_id: int
    party_name: str
    total_scraped: int
    new_politicians: int
    updated_politicians: int
    skipped_politicians: int
    error_count: int
    processing_time_seconds: float
    processed_at: datetime
    errors: list[str] | None = None


class SyncPoliticianScraper:
    """同期的に政治家抽出処理を実行するクラス"""

    def __init__(self, party_id: int, party_name: str):
        """初期化

        Args:
            party_id: 処理対象の政党ID
            party_name: 政党名（ログ表示用）
        """
        self.party_id = party_id
        self.party_name = party_name
        self.logger = ProcessingLogger()
        # 政党IDを直接使用（会議IDの代わり）
        self.log_key = party_id

    async def process(self) -> SyncPoliticianScrapingResult:
        """政治家抽出処理を実行する

        Returns:
            処理結果
        """
        start_time = datetime.now()
        errors: list[str] = []

        try:
            self.logger.add_log(self.log_key, "処理を開始します", "info")
            self.logger.add_log(
                self.log_key,
                f"🎯 {self.party_name}の政治家抽出処理を実行します",
                "info",
            )

            # DIコンテナを使用してUseCaseを取得
            container = init_container()
            scrape_politicians_usecase = (
                container.use_cases.scrape_politicians_usecase()
            )

            # 入力DTOを作成
            input_dto = ScrapePoliticiansInputDTO(
                party_id=self.party_id,
                all_parties=False,
                dry_run=False,
            )

            self.logger.add_log(
                self.log_key,
                f"📋 {self.party_name}の議員一覧ページから政治家情報を取得中...",
                "info",
            )

            # UseCaseを実行
            self.logger.add_log(
                self.log_key,
                "⚙️ UseCase実行中...",
                "info",
            )
            result = await scrape_politicians_usecase.execute(input_dto)

            self.logger.add_log(
                self.log_key,
                f"✅ UseCase実行完了 - {len(result)}件の結果",
                "success",
            )

            # 結果を解析
            total_scraped = len(result)
            new_politicians = 0
            updated_politicians = 0
            skipped_politicians = 0
            error_count = 0

            if result:
                # 詳細情報をログに出力
                details_lines = ["【抽出された政治家】"]
                for i, politician in enumerate(result[:10], 1):
                    # IDが0の場合は新規とみなす
                    status = "🆕 新規" if politician.id == 0 else "📌 既存"
                    if politician.id == 0:
                        new_politicians += 1
                    else:
                        updated_politicians += 1

                    details_lines.append(f"  {i}. {politician.name} - {status}")

                if len(result) > 10:
                    details_lines.append(f"  ... 他{len(result) - 10}人")

                self.logger.add_log(
                    self.log_key,
                    f"📊 抽出結果詳細 ({total_scraped}人)",
                    "info",
                    details="\n".join(details_lines),
                )

            # 処理完了時間を計算
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            # サマリーをログに出力
            summary_lines = [
                f"✅ {self.party_name}の政治家抽出が完了しました",
                f"  • 総抽出数: {total_scraped}人",
                f"  • 新規作成: {new_politicians}人",
                f"  • 更新: {updated_politicians}人",
                f"  • スキップ: {skipped_politicians}人",
            ]
            if error_count > 0:
                summary_lines.append(f"  • エラー: {error_count}件")

            self.logger.add_log(
                self.log_key,
                "\n".join(summary_lines),
                "success",
            )

            self.logger.add_log(
                self.log_key, f"処理時間: {processing_time:.2f}秒", "info"
            )

            return SyncPoliticianScrapingResult(
                party_id=self.party_id,
                party_name=self.party_name,
                total_scraped=total_scraped,
                new_politicians=new_politicians,
                updated_politicians=updated_politicians,
                skipped_politicians=skipped_politicians,
                error_count=error_count,
                processing_time_seconds=processing_time,
                processed_at=end_time,
                errors=errors if errors else None,
            )

        except Exception as e:
            error_msg = str(e)
            self.logger.add_log(
                self.log_key, f"❌ エラーが発生しました: {error_msg}", "error"
            )
            logger.error(
                f"Processing failed for party {self.party_id}: {e}", exc_info=True
            )

            # エラーでも結果を返す
            return SyncPoliticianScrapingResult(
                party_id=self.party_id,
                party_name=self.party_name,
                total_scraped=0,
                new_politicians=0,
                updated_politicians=0,
                skipped_politicians=0,
                error_count=1,
                processing_time_seconds=(datetime.now() - start_time).total_seconds(),
                processed_at=datetime.now(),
                errors=[error_msg],
            )
