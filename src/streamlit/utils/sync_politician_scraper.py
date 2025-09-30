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
            # 処理開始の大きな区切り
            self.logger.add_log(
                self.log_key,
                "=" * 50,
                "info",
            )

            self.logger.add_log(
                self.log_key,
                f"🚀 【処理開始】 {self.party_name}の政治家抽出処理",
                "info",
            )

            self.logger.add_log(
                self.log_key,
                "=" * 50,
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
                # 抽出された政治家を分類
                all_politicians = []
                new_politicians_list = []
                updated_politicians_list = []

                for politician in result:
                    # IDが0の場合は新規とみなす
                    if politician.id == 0:
                        new_politicians += 1
                        new_politicians_list.append(politician)
                    else:
                        updated_politicians += 1
                        updated_politicians_list.append(politician)
                    all_politicians.append(politician)

                # 全体の抽出結果サマリーを表示
                self.logger.add_log(
                    self.log_key,
                    f"✅ {self.party_name}から{total_scraped}人の政治家を抽出しました",
                    "success",
                )

                # 詳細情報を折りたたみで表示（全政治家リスト）
                if all_politicians:
                    details_lines = ["【抽出された政治家一覧】"]
                    for i, politician in enumerate(all_politicians[:30], 1):
                        status = "🆕" if politician.id == 0 else "📌"
                        district = (
                            f" ({politician.district})" if politician.district else ""
                        )
                        details_lines.append(
                            f"  {i}. {status} {politician.name}{district}"
                        )
                    if len(all_politicians) > 30:
                        details_lines.append(f"  ... 他{len(all_politicians) - 30}人")

                    self.logger.add_log(
                        self.log_key,
                        f"📊 政治家詳細 ({total_scraped}人)",
                        "details",
                        details="\n".join(details_lines),
                    )

                # 新規追加された政治家の詳細（折りたたみ）
                if new_politicians_list:
                    new_details = ["【新規追加された政治家】"]
                    for politician in new_politicians_list[:20]:
                        district = (
                            f" ({politician.district})" if politician.district else ""
                        )
                        new_details.append(f"  • {politician.name}{district}")
                    if len(new_politicians_list) > 20:
                        new_details.append(
                            f"  ... 他{len(new_politicians_list) - 20}人"
                        )

                    self.logger.add_log(
                        self.log_key,
                        f"🆕 新規追加 ({new_politicians}人)",
                        "details",
                        details="\n".join(new_details),
                    )

                # 更新された政治家の詳細（折りたたみ）
                if updated_politicians_list:
                    updated_details = ["【情報が更新された政治家】"]
                    for politician in updated_politicians_list[:20]:
                        district = (
                            f" ({politician.district})" if politician.district else ""
                        )
                        updated_details.append(f"  • {politician.name}{district}")
                    if len(updated_politicians_list) > 20:
                        updated_details.append(
                            f"  ... 他{len(updated_politicians_list) - 20}人"
                        )

                    self.logger.add_log(
                        self.log_key,
                        f"📌 情報更新 ({updated_politicians}人)",
                        "details",
                        details="\n".join(updated_details),
                    )

            # 処理完了時間を計算
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            # 処理完了の大きな区切り
            self.logger.add_log(
                self.log_key,
                "=" * 50,
                "info",
            )

            # 処理完了メッセージ
            self.logger.add_log(
                self.log_key,
                f"🎉 【処理完了】 {self.party_name}の政治家抽出が完了しました",
                "success",
            )

            # 統計情報のサマリー
            stats_text = (
                f"総数{total_scraped}人 "
                f"(新規{new_politicians}人, 更新{updated_politicians}人)"
            )
            self.logger.add_log(
                self.log_key,
                f"📈 抽出結果: {stats_text}",
                "info",
            )

            # 処理時間
            self.logger.add_log(
                self.log_key, f"⏱️ 処理時間: {processing_time:.2f}秒", "info"
            )

            # 処理完了の大きな区切り
            self.logger.add_log(
                self.log_key,
                "=" * 50,
                "info",
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

            # エラー時の区切り
            self.logger.add_log(
                self.log_key,
                "=" * 50,
                "info",
            )

            self.logger.add_log(
                self.log_key, "❌ 【処理失敗】 エラーが発生しました", "error"
            )

            self.logger.add_log(self.log_key, f"エラー内容: {error_msg}", "error")

            self.logger.add_log(
                self.log_key,
                "=" * 50,
                "info",
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
