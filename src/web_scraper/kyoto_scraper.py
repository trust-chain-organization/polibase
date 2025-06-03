"""京都市議会議事録スクレーパー"""
import asyncio
import re
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import parse_qs, urlparse

from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, MinutesData


class KyotoCouncilScraper(BaseScraper):
    """京都市議会議事録スクレーパー
    
    URLパターン:
    https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=6030&schedule_id=1
    """
    
    def __init__(self, headless: bool = True):
        super().__init__()
        self.headless = headless
        self.base_url = "https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html"
    
    async def fetch_minutes(self, url: str) -> Optional[MinutesData]:
        """指定されたURLから議事録を取得"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            try:
                page = await browser.new_page()
                
                # ページを読み込み
                await page.goto(url, wait_until="networkidle", timeout=30000)
                
                # JavaScriptレンダリング待機
                await self._wait_for_content(page)
                
                # HTML取得
                html = await page.content()
                
                # パラメータ抽出
                parsed_url = urlparse(url)
                params = parse_qs(parsed_url.query)
                council_id = params.get('council_id', [''])[0]
                schedule_id = params.get('schedule_id', [''])[0]
                
                # データ抽出
                title = await self._extract_title(page)
                date = await self._extract_date(page)
                content = await self.extract_minutes_text(html)
                speakers = await self.extract_speakers(html)
                pdf_url = await self._extract_pdf_url(page)
                
                return MinutesData(
                    council_id=council_id,
                    schedule_id=schedule_id,
                    title=title,
                    date=date,
                    content=content,
                    speakers=speakers,
                    url=url,
                    pdf_url=pdf_url,
                    scraped_at=datetime.now()
                )
                
            except Exception as e:
                self.logger.error(f"Error fetching minutes from {url}: {e}")
                return None
            finally:
                await browser.close()
    
    async def _wait_for_content(self, page: Page):
        """議事録コンテンツの読み込みを待機"""
        # 議事録本文のコンテナが表示されるまで待機
        try:
            await page.wait_for_selector('#plain-minute', timeout=20000)
            # 追加の待機時間（コンテンツの動的読み込み完了まで）
            await asyncio.sleep(2)
        except:
            # セレクタが見つからない場合は別のセレクタを試す
            try:
                await page.wait_for_selector('.minute-content', timeout=10000)
            except:
                self.logger.warning("Could not find expected content selectors")
    
    async def _extract_title(self, page: Page) -> str:
        """ページからタイトルを抽出"""
        try:
            # タイトル要素のセレクタを試行
            selectors = [
                'h1.minute-title',
                'h2.minute-title',
                '.title-area',
                'title'
            ]
            
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    return await element.text_content()
            
            # フォールバック: ページタイトル
            return await page.title()
        except:
            return "議事録"
    
    async def _extract_date(self, page: Page) -> Optional[datetime]:
        """ページから日付を抽出"""
        try:
            # 日付要素のセレクタを試行
            selectors = [
                '.date-info',
                '.minute-date',
                '.meeting-date'
            ]
            
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    date_text = await element.text_content()
                    return self.parse_japanese_date(date_text.strip())
            
            # ページ全体から日付パターンを検索
            content = await page.content()
            date_patterns = [
                r'令和\d+年\d+月\d+日',
                r'平成\d+年\d+月\d+日',
                r'\d{4}年\d+月\d+日'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, content)
                if match:
                    return self.parse_japanese_date(match.group())
            
            return None
        except:
            return None
    
    async def _extract_pdf_url(self, page: Page) -> Optional[str]:
        """PDFダウンロードリンクを抽出"""
        try:
            # PDFリンクのセレクタを試行
            selectors = [
                'a[href*=".pdf"]',
                'a:has-text("PDF")',
                'a:has-text("ダウンロード")'
            ]
            
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    href = await element.get_attribute('href')
                    if href:
                        # 相対URLを絶対URLに変換
                        if not href.startswith('http'):
                            base = f"{page.url.split('?')[0]}"
                            href = f"{base}/{href}".replace('//', '/')
                        return href
            
            return None
        except:
            return None
    
    async def extract_minutes_text(self, html_content: str) -> str:
        """HTMLから議事録テキストを抽出"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 議事録本文のコンテナを探す
        content_selectors = [
            '#plain-minute',
            '.minute-content',
            '.meeting-record',
            'main'
        ]
        
        for selector in content_selectors:
            if selector.startswith('#'):
                element = soup.find(id=selector[1:])
            elif selector.startswith('.'):
                element = soup.find(class_=selector[1:])
            else:
                element = soup.find(selector)
            
            if element:
                # 不要な要素を削除
                for script in element.find_all(['script', 'style']):
                    script.decompose()
                
                # テキストを抽出
                text = element.get_text(separator='\n', strip=True)
                if text and len(text) > 100:  # 有効なコンテンツか確認
                    return text
        
        # フォールバック: body全体から抽出
        body = soup.find('body')
        if body:
            for script in body.find_all(['script', 'style']):
                script.decompose()
            return body.get_text(separator='\n', strip=True)
        
        return ""
    
    async def extract_speakers(self, html_content: str) -> List[Dict[str, str]]:
        """HTMLから発言者情報を抽出"""
        soup = BeautifulSoup(html_content, 'html.parser')
        speakers = []
        
        # 発言者パターンを検索
        # 例: 【山田太郎議員】、○山田太郎議員、山田太郎議員：
        speaker_patterns = [
            r'【([^】]+)】',
            r'○([^（\s]+)(?:議員|委員|市長|局長|部長)',
            r'^([^：\s]+)(?:議員|委員|市長|局長|部長)：'
        ]
        
        content = soup.get_text()
        lines = content.split('\n')
        
        current_speaker = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 発言者を検出
            speaker_found = False
            for pattern in speaker_patterns:
                match = re.search(pattern, line)
                if match:
                    # 前の発言者の内容を保存
                    if current_speaker and current_content:
                        speakers.append({
                            "name": current_speaker,
                            "content": '\n'.join(current_content).strip()
                        })
                    
                    current_speaker = match.group(1).strip()
                    current_content = [line[match.end():].strip()]
                    speaker_found = True
                    break
            
            # 発言者が見つからない場合は現在の発言に追加
            if not speaker_found and current_speaker:
                current_content.append(line)
        
        # 最後の発言者の内容を保存
        if current_speaker and current_content:
            speakers.append({
                "name": current_speaker,
                "content": '\n'.join(current_content).strip()
            })
        
        return speakers