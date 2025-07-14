"""CLI commands for web scraping operations"""

import asyncio
import sys
from pathlib import Path

import click

from ..base import BaseCommand, with_error_handling
from ..progress import ProgressTracker, spinner


class ScrapingCommands(BaseCommand):
    """Commands for scraping meeting minutes and related data"""

    @staticmethod
    @click.command()
    @click.argument("url")
    @click.option(
        "--output-dir",
        default="data/scraped",
        help="Output directory for scraped content",
    )
    @click.option(
        "--format",
        type=click.Choice(["txt", "json", "both"]),
        default="both",
        help="Output format",
    )
    @click.option("--no-cache", is_flag=True, help="Ignore cache and force re-scraping")
    @click.option(
        "--upload-to-gcs",
        is_flag=True,
        help="Upload scraped files to Google Cloud Storage",
    )
    @click.option(
        "--gcs-bucket", help="GCS bucket name (overrides environment variable)"
    )
    @with_error_handling
    def scrape_minutes(
        url: str,
        output_dir: str,
        format: str,
        no_cache: bool,
        upload_to_gcs: bool,
        gcs_bucket: str | None,
    ):
        """Scrape meeting minutes from council website (議事録Web取得)

        This command fetches meeting minutes from supported council websites
        and saves them as text or JSON files.

        Example:
            polibase scrape-minutes "https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=6030&schedule_id=1"
        """
        ScrapingCommands.show_progress(f"Scraping minutes from: {url}")

        # Run the async scraping operation
        success = asyncio.run(
            ScrapingCommands._async_scrape_minutes(
                url, output_dir, format, no_cache, upload_to_gcs, gcs_bucket
            )
        )

        sys.exit(0 if success else 1)

    @staticmethod
    async def _async_scrape_minutes(
        url: str,
        output_dir: str,
        format: str,
        no_cache: bool,
        upload_to_gcs: bool,
        gcs_bucket: str | None,
    ):
        """Async implementation of scrape_minutes"""
        import os

        from src.database.meeting_repository import MeetingRepository
        from src.web_scraper.scraper_service import ScraperService

        # GCS設定の上書き
        if gcs_bucket:
            os.environ["GCS_BUCKET_NAME"] = gcs_bucket

        # サービス初期化
        with spinner("Initializing scraper service"):
            service = ScraperService(enable_gcs=upload_to_gcs)

        # スクレイピング実行
        with spinner(f"Fetching minutes from: {url}") as spin:
            minutes = await service.fetch_from_url(url, use_cache=not no_cache)
            spin.stop(
                "✓ Minutes fetched successfully"
                if minutes
                else "✗ Failed to fetch minutes"
            )
        if not minutes:
            ScrapingCommands.error("Failed to scrape minutes", exit_code=0)
            return False

        # 出力ディレクトリ作成
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # ファイル名生成
        base_name = f"{minutes.council_id}_{minutes.schedule_id}"

        # GCS URIを保存するための変数
        gcs_text_uri = None
        gcs_pdf_uri = None

        # テキスト形式で保存
        if format in ["txt", "both"]:
            txt_path = output_path / f"{base_name}.txt"
            success, gcs_url = service.export_to_text(
                minutes, str(txt_path), upload_to_gcs=upload_to_gcs
            )
            if success:
                ScrapingCommands.show_progress(f"Saved text to: {txt_path}")
                if gcs_url:
                    ScrapingCommands.show_progress(f"Uploaded to GCS: {gcs_url}")
                    gcs_text_uri = gcs_url
            else:
                ScrapingCommands.error("Failed to save text file", exit_code=0)

        # JSON形式で保存
        if format in ["json", "both"]:
            json_path = output_path / f"{base_name}.json"
            success, gcs_url = service.export_to_json(
                minutes, str(json_path), upload_to_gcs=upload_to_gcs
            )
            if success:
                ScrapingCommands.show_progress(f"Saved JSON to: {json_path}")
                if gcs_url:
                    ScrapingCommands.show_progress(f"Uploaded to GCS: {gcs_url}")
            else:
                ScrapingCommands.error("Failed to save JSON file", exit_code=0)

        # PDFをGCSにアップロード（PDFがローカルに保存されている場合）
        if upload_to_gcs and minutes.pdf_url:
            pdf_path = output_path / f"{base_name}.pdf"
            if pdf_path.exists():
                gcs_url = service.upload_pdf_to_gcs(str(pdf_path), minutes)
                if gcs_url:
                    ScrapingCommands.show_progress(f"Uploaded PDF to GCS: {gcs_url}")
                    gcs_pdf_uri = gcs_url

        # meetingsテーブルのGCS URIを更新（URLから既存のmeetingを検索して更新）
        if gcs_text_uri or gcs_pdf_uri:
            try:
                with spinner("Updating meeting record with GCS URIs"):
                    repo = MeetingRepository()
                    # URLでmeetingを検索（パラメータの順序が異なる場合も考慮）
                    # 完全一致で検索
                    meetings = repo.fetch_as_dict(
                        "SELECT id FROM meetings WHERE url = :url", {"url": url}
                    )

                    # 完全一致で見つからない場合、LIKE検索を試す
                    if not meetings:
                        # minIdがURLに含まれている場合の処理
                        if "minId=" in url:
                            min_id = url.split("minId=")[1].split("&")[0]
                            meetings = repo.fetch_as_dict(
                                "SELECT id FROM meetings WHERE url LIKE :pattern",
                                {"pattern": f"%minId={min_id}%"},
                            )
                    if meetings:
                        meeting_id = meetings[0]["id"]
                        success = repo.update_meeting_gcs_uris(
                            meeting_id, gcs_pdf_uri, gcs_text_uri
                        )
                        if success:
                            ScrapingCommands.show_progress(
                                f"Updated meeting {meeting_id} with GCS URIs"
                            )
                    repo.close()
            except Exception as e:
                ScrapingCommands.show_progress(
                    f"Note: Could not update meeting record: {e}"
                )

        # 基本情報を表示
        ScrapingCommands.show_progress("\n--- Minutes Summary ---")
        ScrapingCommands.show_progress(f"Title: {minutes.title}")
        date_str = minutes.date.strftime("%Y年%m月%d日") if minutes.date else "Unknown"
        ScrapingCommands.show_progress(f"Date: {date_str}")
        ScrapingCommands.show_progress(f"Speakers found: {len(minutes.speakers)}")
        ScrapingCommands.show_progress(
            f"Content length: {len(minutes.content)} characters"
        )
        if minutes.pdf_url:
            ScrapingCommands.show_progress(f"PDF URL: {minutes.pdf_url}")

        return True

    @staticmethod
    @click.command()
    @click.option(
        "--tenant",
        required=True,
        help="Tenant name in kaigiroku.net (e.g., kyoto, osaka, kobe)",
    )
    @click.option("--start-id", default=6000, help="Start council ID")
    @click.option("--end-id", default=6100, help="End council ID")
    @click.option("--max-schedule", default=10, help="Maximum schedule ID to try")
    @click.option("--output-dir", default="data/scraped/batch", help="Output directory")
    @click.option("--concurrent", default=3, help="Number of concurrent requests")
    @click.option(
        "--upload-to-gcs",
        is_flag=True,
        help="Upload scraped files to Google Cloud Storage",
    )
    @click.option(
        "--gcs-bucket", help="GCS bucket name (overrides environment variable)"
    )
    @with_error_handling
    def batch_scrape(
        tenant: str,
        start_id: int,
        end_id: int,
        max_schedule: int,
        output_dir: str,
        concurrent: int,
        upload_to_gcs: bool,
        gcs_bucket: str | None,
    ):
        """Batch scrape multiple meeting minutes from kaigiroku.net (議事録一括取得)

        This command tries to scrape multiple meeting minutes from kaigiroku.net
        by iterating through council and schedule IDs.

        Examples:
            polibase batch-scrape --tenant kyoto --start-id 6000 --end-id 6010
            polibase batch-scrape --tenant osaka --start-id 1000 --end-id 1100
        """
        ScrapingCommands.show_progress(
            f"Batch scraping from kaigiroku.net tenant: {tenant}"
        )
        ScrapingCommands.show_progress(f"Council IDs: {start_id} to {end_id}")
        ScrapingCommands.show_progress(f"Schedule IDs: 1 to {max_schedule}")

        # URL生成
        base_url = f"https://ssp.kaigiroku.net/tenant/{tenant}/MinuteView.html"
        urls: list[str] = []
        for council_id in range(start_id, end_id + 1):
            for schedule_id in range(1, max_schedule + 1):
                url = f"{base_url}?council_id={council_id}&schedule_id={schedule_id}"
                urls.append(url)

        ScrapingCommands.show_progress(f"Total URLs to try: {len(urls)}")

        if not ScrapingCommands.confirm("Do you want to continue?"):
            return

        # Run the async batch processing
        success_count = asyncio.run(
            ScrapingCommands._async_batch_scrape(
                urls, output_dir, concurrent, upload_to_gcs, gcs_bucket
            )
        )

        ScrapingCommands.success(
            f"Saved {success_count} meeting minutes to {output_dir}"
        )

    @staticmethod
    async def _async_batch_scrape(
        urls: list[str],
        output_dir: str,
        concurrent: int,
        upload_to_gcs: bool,
        gcs_bucket: str | None,
    ):
        """Async implementation of batch_scrape"""
        import os

        from src.web_scraper.scraper_service import ScraperService

        # GCS設定の上書き
        if gcs_bucket:
            os.environ["GCS_BUCKET_NAME"] = gcs_bucket

        # サービス初期化
        service = ScraperService(enable_gcs=upload_to_gcs)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # バッチ処理実行
        success_count = 0

        with ProgressTracker(len(urls), "Scraping minutes") as tracker:
            results = await service.fetch_multiple(urls, max_concurrent=concurrent)

            for i, minutes in enumerate(results):
                tracker.update(1, f"Processing {i + 1}/{len(urls)}")
                if minutes:
                    # テキストとJSONで保存
                    base_name = f"{minutes.council_id}_{minutes.schedule_id}"
                    txt_path = output_path / f"{base_name}.txt"
                    json_path = output_path / f"{base_name}.json"

                    # テキスト形式で保存（GCS対応）
                    txt_success, txt_gcs_url = service.export_to_text(
                        minutes, str(txt_path), upload_to_gcs=upload_to_gcs
                    )

                    # JSON形式で保存（GCS対応）
                    json_success, json_gcs_url = service.export_to_json(
                        minutes, str(json_path), upload_to_gcs=upload_to_gcs
                    )

                    if txt_success and json_success:
                        success_count += 1
                        if txt_gcs_url or json_gcs_url:
                            ScrapingCommands.show_progress(
                                f"Scraped and uploaded: {base_name}"
                            )

        ScrapingCommands.show_progress(
            f"\nCompleted: {success_count}/{len(urls)} URLs successfully scraped"
        )
        return success_count


def get_scraping_commands():
    """Get all scraping-related commands"""
    return [ScrapingCommands.scrape_minutes, ScrapingCommands.batch_scrape]
