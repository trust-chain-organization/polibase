"""HTML fetcher for party member pages with pagination support"""

import asyncio
import logging
from types import TracebackType

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from ..config.settings import get_settings
from .models import WebPageContent

logger = logging.getLogger(__name__)


class PartyMemberPageFetcher:
    """政党の議員一覧ページを取得（ページネーション対応）"""

    def __init__(self):
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.settings = get_settings()

    async def __aenter__(self):
        try:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            self.context = await self.browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            return self
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
        except Exception:
            # 終了時のエラーは無視
            pass

    async def fetch_all_pages(
        self, start_url: str, max_pages: int = 20
    ) -> list[WebPageContent]:
        """
        議員一覧ページを取得（ページネーション対応）

        Args:
            start_url: 開始URL
            max_pages: 最大ページ数

        Returns:
            List[WebPageContent]: 取得したページコンテンツのリスト
        """
        pages_content: list[WebPageContent] = []
        visited_urls: set[str] = set()

        if not self.context:
            raise RuntimeError("Browser context not initialized")

        page = await self.context.new_page()
        try:
            # 最初のページを取得
            logger.info(f"Fetching initial page: {start_url}")
            await page.goto(
                start_url,
                wait_until="networkidle",
                timeout=self.settings.page_load_timeout * 1000,
            )
            await asyncio.sleep(2)  # 動的コンテンツの読み込み待機

            current_page_num = 1

            while current_page_num <= max_pages:
                # 現在のページのコンテンツを取得
                current_url = page.url
                if current_url in visited_urls:
                    logger.info("Already visited this URL, stopping pagination")
                    break

                visited_urls.add(current_url)
                content = await page.content()

                pages_content.append(
                    WebPageContent(
                        url=current_url,
                        html_content=content,
                        page_number=current_page_num,
                    )
                )

                logger.info(f"Fetched page {current_page_num}: {current_url}")

                # 次のページへのリンクを探す
                next_link = await self._find_next_page_link(page)

                if not next_link:
                    logger.info("No more pages found")
                    break

                # 次のページへ移動
                try:
                    logger.info("Attempting to click next page link")
                    await next_link.click()
                    await page.wait_for_load_state(
                        "networkidle", timeout=self.settings.page_load_timeout * 1000
                    )
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.warning(f"Failed to navigate to next page: {e}")
                    break

                current_page_num += 1

            return pages_content

        except Exception as e:
            logger.error(f"Error during page fetching from {start_url}: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            # エラーが発生しても、取得済みのページは返す
            return pages_content if pages_content else []
        finally:
            await page.close()

    async def _find_next_page_link(self, page: Page):
        """次のページへのリンクを探す"""
        # 一般的なページネーションパターン
        next_patterns = [
            'a:has-text("次へ")',
            'a:has-text("次")',
            'a:has-text("Next")',
            'a:has-text(">")',
            'a:has-text("»")',
            'a[rel="next"]',
            ".pagination a.next",
            ".pager a.next",
            "a.page-next",
            "li.next a",
        ]

        for pattern in next_patterns:
            try:
                element = await page.query_selector(pattern)
                if element and await element.is_visible():
                    # リンクが無効化されていないか確認
                    is_disabled = (
                        await element.get_attribute("disabled")
                        or await element.get_attribute("aria-disabled") == "true"
                        or "disabled" in (await element.get_attribute("class") or "")
                    )

                    if not is_disabled:
                        return element
            except Exception:
                continue

        # 数字のページネーション（現在のページ番号の次）
        try:
            # 現在のページ番号を特定
            current_page_elem = await page.query_selector(
                ".pagination .active, .pager .current, .page-current"
            )
            if current_page_elem:
                current_text = await current_page_elem.text_content()
                if current_text and current_text.strip().isdigit():
                    current_num = int(current_text.strip())
                    next_num = current_num + 1

                    # 次のページ番号のリンクを探す
                    next_link = await page.query_selector(f'a:has-text("{next_num}")')
                    if next_link and await next_link.is_visible():
                        return next_link
        except Exception:
            pass

        return None

    async def fetch_single_page(self, url: str) -> WebPageContent | None:
        """単一ページを取得"""
        if not self.context:
            raise RuntimeError("Browser context not initialized")

        page = await self.context.new_page()
        try:
            logger.info(f"Fetching page: {url}")
            await page.goto(
                url,
                wait_until="networkidle",
                timeout=self.settings.page_load_timeout * 1000,
            )
            await asyncio.sleep(2)

            content = await page.content()
            return WebPageContent(url=url, html_content=content, page_number=1)

        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            return None
        finally:
            await page.close()
