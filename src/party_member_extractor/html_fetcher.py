"""HTML fetcher for party member pages with pagination support"""
import asyncio
import logging
from typing import List, Optional, Tuple
from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup
import re
from .models import WebPageContent

logger = logging.getLogger(__name__)


class PartyMemberPageFetcher:
    """政党の議員一覧ページを取得（ページネーション対応）"""
    
    def __init__(self):
        self.browser = None
        self.context = None
    
    async def __aenter__(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
    
    async def fetch_all_pages(self, start_url: str, max_pages: int = 20) -> List[WebPageContent]:
        """
        議員一覧ページを取得（ページネーション対応）
        
        Args:
            start_url: 開始URL
            max_pages: 最大ページ数
            
        Returns:
            List[WebPageContent]: 取得したページコンテンツのリスト
        """
        pages_content = []
        visited_urls = set()
        
        page = await self.context.new_page()
        try:
            # 最初のページを取得
            logger.info(f"Fetching initial page: {start_url}")
            await page.goto(start_url, wait_until='networkidle', timeout=30000)
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
                
                pages_content.append(WebPageContent(
                    url=current_url,
                    html_content=content,
                    page_number=current_page_num
                ))
                
                logger.info(f"Fetched page {current_page_num}: {current_url}")
                
                # 次のページへのリンクを探す
                next_link = await self._find_next_page_link(page)
                
                if not next_link:
                    logger.info("No more pages found")
                    break
                
                # 次のページへ移動
                logger.info(f"Moving to next page: {next_link}")
                await next_link.click()
                await page.wait_for_load_state('networkidle', timeout=30000)
                await asyncio.sleep(2)
                
                current_page_num += 1
            
            return pages_content
            
        except Exception as e:
            logger.error(f"Error fetching pages: {e}")
            return pages_content
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
            '.pagination a.next',
            '.pager a.next',
            'a.page-next',
            'li.next a',
        ]
        
        for pattern in next_patterns:
            try:
                element = await page.query_selector(pattern)
                if element and await element.is_visible():
                    # リンクが無効化されていないか確認
                    is_disabled = await element.get_attribute('disabled') or \
                                 await element.get_attribute('aria-disabled') == 'true' or \
                                 'disabled' in (await element.get_attribute('class') or '')
                    
                    if not is_disabled:
                        return element
            except:
                continue
        
        # 数字のページネーション（現在のページ番号の次）
        try:
            # 現在のページ番号を特定
            current_page_elem = await page.query_selector('.pagination .active, .pager .current, .page-current')
            if current_page_elem:
                current_text = await current_page_elem.text_content()
                if current_text and current_text.strip().isdigit():
                    current_num = int(current_text.strip())
                    next_num = current_num + 1
                    
                    # 次のページ番号のリンクを探す
                    next_link = await page.query_selector(f'a:has-text("{next_num}")')
                    if next_link and await next_link.is_visible():
                        return next_link
        except:
            pass
        
        return None
    
    async def fetch_single_page(self, url: str) -> Optional[WebPageContent]:
        """単一ページを取得"""
        page = await self.context.new_page()
        try:
            logger.info(f"Fetching page: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            content = await page.content()
            return WebPageContent(
                url=url,
                html_content=content,
                page_number=1
            )
            
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            return None
        finally:
            await page.close()