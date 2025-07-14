"""CLI commands for politician data processing"""

import asyncio
import time

import click
from sqlalchemy import text

from ..base import BaseCommand, with_error_handling
from ..progress import ProgressTracker, spinner


class PoliticianCommands(BaseCommand):
    """Commands for processing politician data"""

    @staticmethod
    @click.command()
    @click.option("--party-id", type=int, help="Specific party ID to scrape")
    @click.option(
        "--all-parties", is_flag=True, help="Scrape all parties with member list URLs"
    )
    @click.option(
        "--dry-run", is_flag=True, help="Show what would be scraped without saving"
    )
    @click.option("--max-pages", default=10, help="Maximum pages to fetch per party")
    @with_error_handling
    def scrape_politicians(
        party_id: int | None, all_parties: bool, dry_run: bool, max_pages: int
    ):
        """Scrape politician data from party member list pages (政党議員一覧取得)

        This command fetches politician information from political party websites
        using LLM to extract structured data and saves them to the database.

        Examples:
            polibase scrape-politicians --party-id 1
            polibase scrape-politicians --all-parties
            polibase scrape-politicians --all-parties --dry-run
        """
        # Run the async scraping operation
        asyncio.run(
            PoliticianCommands._async_scrape_politicians(
                party_id, all_parties, dry_run, max_pages
            )
        )

    @staticmethod
    async def _async_scrape_politicians(
        party_id: int | None, all_parties: bool, dry_run: bool, max_pages: int
    ):
        """Async implementation of scrape_politicians"""
        from src.config.database import get_db_engine
        from src.database.politician_repository import PoliticianRepository
        from src.party_member_extractor.extractor import PartyMemberExtractor
        from src.party_member_extractor.html_fetcher import PartyMemberPageFetcher

        engine = get_db_engine()

        try:
            # 対象の政党を取得
            with engine.connect() as conn:
                if party_id:
                    query = text("""
                        SELECT id, name, members_list_url
                        FROM political_parties
                        WHERE id = :party_id AND members_list_url IS NOT NULL
                    """)
                    result = conn.execute(query, {"party_id": party_id})
                else:
                    query = text("""
                        SELECT id, name, members_list_url
                        FROM political_parties
                        WHERE members_list_url IS NOT NULL
                        ORDER BY name
                    """)
                    result = conn.execute(query)

                parties = result.fetchall()

            if not parties:
                PoliticianCommands.error(
                    "No parties found with member list URLs", exit_code=0
                )
                return

            PoliticianCommands.show_progress(f"Found {len(parties)} parties to scrape:")
            for party in parties:
                PoliticianCommands.show_progress(
                    f"  - {party.name}: {party.members_list_url}"
                )

            # Streamlitから実行される場合は確認をスキップ
            import os

            if os.environ.get("STREAMLIT_RUNNING") != "true":
                if not PoliticianCommands.confirm("\nDo you want to continue?"):
                    return

            # スクレイピング実行
            total_scraped = 0

            # HTMLフェッチャーとエクストラクターを初期化
            with spinner("Initializing extractors"):
                extractor = PartyMemberExtractor()

            async with PartyMemberPageFetcher() as fetcher:
                with ProgressTracker(len(parties), "Processing parties") as tracker:
                    for _i, party in enumerate(parties):
                        PoliticianCommands.show_progress(
                            f"\nProcessing {party.name}..."
                        )
                        PoliticianCommands.show_progress(
                            f"  URL: {party.members_list_url}"
                        )

                        # HTMLページを取得（ページネーション対応）
                        with spinner(
                            f"Fetching pages from {party.name} (max: {max_pages})..."
                        ):
                            pages = await fetcher.fetch_all_pages(
                                party.members_list_url, max_pages=max_pages
                            )

                        if not pages:
                            PoliticianCommands.show_progress(
                                f"  Failed to fetch pages for {party.name}"
                            )
                            continue

                        PoliticianCommands.show_progress(
                            f"  Fetched {len(pages)} pages"
                        )

                        # LLMで議員情報を抽出
                        with spinner(
                            f"Extracting member information using LLM "
                            f"for {party.name}..."
                        ):
                            result = extractor.extract_from_pages(pages, party.name)

                        if not result or not result.members:
                            PoliticianCommands.show_progress(
                                f"  No members found for {party.name}"
                            )
                            continue

                        PoliticianCommands.show_progress(
                            f"  Extracted {len(result.members)} members"
                        )

                        if dry_run:
                            # ドライランモード：データを表示するだけ
                            for member in result.members[:5]:  # 最初の5件を表示
                                PoliticianCommands.show_progress(f"    - {member.name}")
                                if member.position:
                                    PoliticianCommands.show_progress(
                                        f"      Position: {member.position}"
                                    )
                                if member.electoral_district:
                                    PoliticianCommands.show_progress(
                                        f"      District: {member.electoral_district}"
                                    )
                                if member.prefecture:
                                    PoliticianCommands.show_progress(
                                        f"      Prefecture: {member.prefecture}"
                                    )
                                if member.party_position:
                                    PoliticianCommands.show_progress(
                                        f"      Party Role: {member.party_position}"
                                    )
                            if len(result.members) > 5:
                                PoliticianCommands.show_progress(
                                    f"    ... and {len(result.members) - 5} more"
                                )
                        else:
                            # データベースに保存
                            with spinner(
                                f"Saving {len(result.members)} members to database..."
                            ):
                                repo = PoliticianRepository()

                                # Pydanticモデルを辞書に変換して
                                # political_party_idを追加
                                members_data = []
                                for member in result.members:
                                    member_dict = member.model_dump()
                                    member_dict["political_party_id"] = party.id
                                    members_data.append(member_dict)

                                stats = repo.bulk_create_politicians(members_data)
                                repo.close()

                            # 統計情報を表示
                            PoliticianCommands.show_progress(
                                "  Database operation results:"
                            )
                            PoliticianCommands.show_progress(
                                f"    - Created: {len(stats['created'])} "
                                "new politicians"
                            )
                            PoliticianCommands.show_progress(
                                f"    - Updated: {len(stats['updated'])} "
                                "existing politicians"
                            )
                            PoliticianCommands.show_progress(
                                f"    - Errors: {len(stats['errors'])}"
                            )

                            total_scraped += len(stats["created"]) + len(
                                stats["updated"]
                            )

                        tracker.update(1, f"Completed {party.name}")

            if not dry_run:
                PoliticianCommands.success(f"Total politicians saved: {total_scraped}")

        finally:
            engine.dispose()
            # 少し待機してから終了
            time.sleep(0.5)


def get_politician_commands():
    """Get all politician-related commands"""
    return [
        PoliticianCommands.scrape_politicians,
    ]
