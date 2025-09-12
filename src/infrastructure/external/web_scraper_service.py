"""Web scraper service interface and implementation."""

from abc import ABC, abstractmethod
from typing import Any


class IWebScraperService(ABC):
    """Interface for web scraping service."""

    @abstractmethod
    def is_supported_url(self, url: str) -> bool:
        """Check if the URL is supported for scraping."""
        pass

    @abstractmethod
    async def scrape_party_members(
        self, url: str, party_id: int, party_name: str | None = None
    ) -> list[dict[str, Any]]:
        """Scrape party members from website."""
        pass

    @abstractmethod
    async def scrape_conference_members(self, url: str) -> list[dict[str, Any]]:
        """Scrape conference members from website."""
        pass

    @abstractmethod
    async def scrape_meeting_minutes(
        self, url: str, upload_to_gcs: bool = False
    ) -> dict[str, Any]:
        """Scrape meeting minutes from website."""
        pass

    @abstractmethod
    async def scrape_proposal_judges(self, url: str) -> list[dict[str, Any]]:
        """Scrape proposal voting information from website."""
        pass


class PlaywrightScraperService(IWebScraperService):
    """Playwright-based implementation of web scraper."""

    def __init__(self, headless: bool = True, llm_service: Any | None = None):
        """Initialize the PlaywrightScraperService.

        Args:
            headless: Whether to run the browser in headless mode
            llm_service: Optional LLM service for content extraction.
                        If not provided, a default GeminiLLMService will be created.
        """
        self.headless = headless
        self._llm_service = llm_service
        # Initialize Playwright here

    def is_supported_url(self, url: str) -> bool:
        """Check if the URL is supported for scraping.

        Args:
            url: URL to check

        Returns:
            True if the URL is supported, False otherwise
        """
        # Support common Japanese government and council websites
        supported_domains = [
            "kaigiroku.net",
            "metro.tokyo.lg.jp",
            "pref.kyoto.lg.jp",
            "pref.osaka.lg.jp",
            "city.kyoto.lg.jp",
            "city.osaka.lg.jp",
            "shugiin.go.jp",
            "sangiin.go.jp",
        ]

        return any(domain in url for domain in supported_domains)

    async def scrape_party_members(
        self, url: str, party_id: int, party_name: str | None = None
    ) -> list[dict[str, Any]]:
        """Scrape party members using Playwright with actual implementation."""
        import asyncio
        import logging

        from src.party_member_extractor.extractor import PartyMemberExtractor
        from src.party_member_extractor.html_fetcher import PartyMemberPageFetcher
        from src.streamlit.utils.processing_logger import ProcessingLogger

        logger = logging.getLogger(__name__)
        # Use a single ProcessingLogger instance throughout the chain
        proc_logger = ProcessingLogger()
        log_key = party_id

        # Get party name if not provided
        if party_name is None:
            # Try to get party name from database
            from sqlalchemy.orm import sessionmaker

            from src.config.database import get_db_engine
            from src.infrastructure.persistence.async_session_adapter import (
                AsyncSessionAdapter,
            )
            from src.infrastructure.persistence.political_party_repository_impl import (
                PoliticalPartyRepositoryImpl,
            )

            engine = get_db_engine()
            session_local = sessionmaker(bind=engine)
            session = session_local()
            async_session = AsyncSessionAdapter(session)
            party_repo = PoliticalPartyRepositoryImpl(async_session)

            try:
                party = await party_repo.get_by_id(party_id)
                if party:
                    party_name = party.name
                else:
                    party_name = "Unknown Party"
            finally:
                session.close()

        try:
            # Log the start of web scraping
            proc_logger.add_log(log_key, f"🌐 Webページを取得中: {url}", "info")

            # Fetch pages with JavaScript rendering support
            fetcher = None
            try:
                # Pass the ProcessingLogger instance to avoid multiple instances
                fetcher = PartyMemberPageFetcher(
                    party_id=party_id, proc_logger=proc_logger
                )
                await fetcher.__aenter__()

                proc_logger.add_log(
                    log_key, "📄 JavaScriptレンダリング後のページを取得中...", "info"
                )

                proc_logger.add_log(
                    log_key, f"🎯 URL: {url}からページを取得開始", "info"
                )

                pages = await fetcher.fetch_all_pages(url, max_pages=10)

                proc_logger.add_log(
                    log_key, f"🎬 fetch_all_pages完了 - {len(pages)}ページ取得", "info"
                )

                if not pages:
                    logger.warning(f"No pages fetched from {url}")
                    proc_logger.add_log(
                        log_key, "⚠️ ページが取得できませんでした", "warning"
                    )
                    return []

                proc_logger.add_log(
                    log_key, f"✅ {len(pages)}ページ取得完了", "success"
                )

                # Log page URLs for debugging
                for i, page in enumerate(pages, 1):
                    proc_logger.add_log(log_key, f"  ページ{i}: {page.url}", "info")

                # Extract party members using LLM
                proc_logger.add_log(log_key, "🤖 LLMで政治家情報を抽出中...", "info")

                # Pass the ProcessingLogger instance to avoid multiple instances
                extractor = PartyMemberExtractor(
                    party_id=party_id, proc_logger=proc_logger
                )
                members_list = extractor.extract_from_pages(pages, party_name)

                # Convert to expected format
                result = []
                if members_list and members_list.members:
                    member_names = []
                    for member in members_list.members:
                        result.append(
                            {
                                "name": member.name,
                                "furigana": None,  # Not available in PartyMemberInfo
                                "position": member.position,
                                "district": member.electoral_district,
                                "profile_image_url": None,  # Not in PartyMemberInfo
                                "profile_page_url": member.profile_url,
                            }
                        )
                        member_names.append(member.name)

                    proc_logger.add_log(
                        log_key, f"✅ {len(result)}人の政治家情報を抽出", "success"
                    )

                    # Log extracted member names for debugging
                    if member_names:
                        names_display = ", ".join(member_names[:10])
                        if len(member_names) > 10:
                            names_display += f" ... 他{len(member_names) - 10}人"
                        proc_logger.add_log(
                            log_key, f"抽出された議員: {names_display}", "info"
                        )

                return result

            finally:
                # Ensure proper cleanup
                if fetcher:
                    await fetcher.__aexit__(None, None, None)
                    # Give asyncio time to clean up
                    await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Failed to scrape party members from {url}: {e}")
            proc_logger.add_log(
                log_key, "❌ 政治家抽出処理でエラーが発生しました", "error"
            )
            proc_logger.add_log(log_key, f"エラー詳細: {str(e)}", "error")

            # エラーの種類に応じたヒントを表示
            if "Timeout" in str(e):
                proc_logger.add_log(
                    log_key,
                    "💡 対処法: タイムアウト。サイトが混雑している可能性があります。",
                    "info",
                )
            elif "Failed to initialize" in str(e):
                proc_logger.add_log(
                    log_key,
                    "💡 対処法: ブラウザ初期化失敗。リソースを確認してください。",
                    "info",
                )
            elif "LLM" in str(e) or "Gemini" in str(e):
                proc_logger.add_log(
                    log_key,
                    "💡 対処法: AI処理エラー。APIキーやクォータを確認してください。",
                    "info",
                )

            # Return empty list on error instead of dummy data
            return []

    async def scrape_conference_members(self, url: str) -> list[dict[str, Any]]:
        """Scrape conference members using Playwright."""
        # Implementation would use Playwright to navigate and extract data
        # This is a placeholder
        return [
            {
                "name": "佐藤花子",
                "party": "○○党",
                "role": "議長",
                "profile_url": "https://example.com/member/1",
            }
        ]

    async def scrape_meeting_minutes(
        self, url: str, upload_to_gcs: bool = False
    ) -> dict[str, Any]:
        """Scrape meeting minutes using Playwright."""
        # Implementation would use Playwright to navigate and extract data
        # This is a placeholder
        return {
            "meeting_date": "2024-01-15",
            "meeting_name": "本会議",
            "pdf_url": "https://example.com/minutes.pdf",
            "text_content": "会議の内容...",
            "gcs_pdf_uri": "gs://bucket/minutes.pdf" if upload_to_gcs else None,
            "gcs_text_uri": "gs://bucket/minutes.txt" if upload_to_gcs else None,
        }

    async def scrape_proposal_judges(self, url: str) -> list[dict[str, Any]]:
        """Scrape proposal voting information from website.

        Args:
            url: URL of the proposal voting results page

        Returns:
            List of voting information with name, party, and judgment
        """
        import logging

        from playwright.async_api import async_playwright

        from src.domain.services.proposal_judge_extraction_service import (
            ProposalJudgeExtractionService,
        )

        logger = logging.getLogger(__name__)

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()

                # Navigate to the URL
                await page.goto(url, wait_until="networkidle")

                # Wait for content to load
                await page.wait_for_load_state("domcontentloaded")

                # Get the page content
                text_content = await page.inner_text("body")

                await browser.close()

                # Use LLM to extract voting information
                # Use injected service or create default
                if self._llm_service:
                    llm_service = self._llm_service
                else:
                    from src.infrastructure.external.llm_service import GeminiLLMService

                    llm_service = GeminiLLMService()

                # Use extract_speeches_from_text which handles JSON extraction
                # We'll format our prompt to work with this method
                formatted_text = f"""
以下のウェブページから議案賛否情報を抽出してください。

ページの内容:
{text_content[:5000]}

各議員について以下の形式で返してください：
- name: 議員名（敬称除去）
- party: 所属政党
- judgment: 賛成/反対/棄権/欠席
"""
                # The method returns a list, so we can use it directly
                judges_data = await llm_service.extract_speeches_from_text(
                    formatted_text
                )

                # The result should already be a list
                if isinstance(judges_data, list):
                    # Normalize the data using domain service
                    normalized_judges = []
                    for judge in judges_data:
                        judgment_text = judge.get("judgment", "")
                        normalized_judgment, is_known = (
                            ProposalJudgeExtractionService.normalize_judgment_type(
                                judgment_text
                            )
                        )

                        # Log unknown judgment types
                        if not is_known:
                            logger.warning(
                                f"Unknown judgment type: {judgment_text}, "
                                f"defaulting to APPROVE"
                            )

                        normalized_judges.append(
                            {
                                "name": (
                                    ProposalJudgeExtractionService.normalize_politician_name(
                                        judge.get("name", "")
                                    )
                                ),
                                "party": judge.get("party"),
                                "judgment": normalized_judgment,
                            }
                        )
                    return normalized_judges

                # If not a list, try text parsing
                return ProposalJudgeExtractionService.parse_voting_result_text(
                    text_content
                )

        except Exception as e:
            logger.error(f"Failed to scrape proposal judges from {url}: {e}")
            return []
