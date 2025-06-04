"""kaigiroku.net議事録システムスクレーパー"""
import asyncio
import re
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import parse_qs, urlparse

from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper, MinutesData


class KaigirokuNetScraper(BaseScraper):
    """kaigiroku.net議事録システム汎用スクレーパー
    
    対応URL例:
    - https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=6030&schedule_id=1
    - https://ssp.kaigiroku.net/tenant/osaka/MinuteView.html?council_id=1234&schedule_id=1
    - https://ssp.kaigiroku.net/tenant/kobe/MinuteView.html?council_id=5678&schedule_id=1
    
    kaigiroku.netは多くの地方議会で使用されている統一システムのため、
    tenant名が異なっても同じ構造で議事録を取得可能です。
    """
    
    def __init__(self, headless: bool = True):
        super().__init__()
        self.headless = headless
    
    async def fetch_minutes(self, url: str) -> Optional[MinutesData]:
        """指定されたURLから議事録を取得"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            try:
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                page = await context.new_page()
                
                self.logger.info(f"Loading URL: {url}")
                
                # ページを読み込み
                response = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                if not response:
                    self.logger.error("No response from server")
                    return None
                    
                self.logger.info(f"Response status: {response.status}")
                
                # JavaScriptの実行を待つ
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(5)  # 追加の待機時間
                
                # まずPDFのダウンロードボタンを探す
                pdf_url = await self._find_pdf_download_url(page)
                if pdf_url:
                    self.logger.info(f"Found PDF URL: {pdf_url}")
                    # PDFをダウンロードして内容を返す
                    return await self._download_pdf_as_minutes(pdf_url, url)
                
                # JavaScriptレンダリング待機
                await self._wait_for_content(page)
                
                # iframeコンテンツの処理
                iframe_content = await self._extract_iframe_content(page)
                
                # HTML取得（iframeコンテンツまたはメインページ）
                if iframe_content:
                    html = iframe_content
                    self.logger.info("Using iframe content")
                else:
                    html = await page.content()
                    self.logger.info("Using main page content")
                
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
                
                # コンテンツが空の場合は、ページ全体のテキストを取得
                if not content or len(content.strip()) < 100:
                    self.logger.warning("Content is too short, trying to extract all text")
                    content = await page.evaluate('document.body.innerText || ""')
                
                # それでも空の場合は、テキスト表示用のURLを試す
                if not content or len(content.strip()) < 100:
                    text_url = await self._find_text_view_url(page)
                    if text_url:
                        self.logger.info(f"Trying text view URL: {text_url}")
                        await page.goto(text_url, wait_until="networkidle")
                        await asyncio.sleep(3)
                        content = await page.evaluate('document.body.innerText || ""')
                
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
                import traceback
                self.logger.error(traceback.format_exc())
                return None
            finally:
                await browser.close()
    
    async def _wait_for_content(self, page: Page):
        """議事録コンテンツの読み込みを待機"""
        # kaigiroku.netの動的コンテンツ読み込みを待機
        self.logger.info("Waiting for content to load...")
        
        # まず基本的なページ読み込みを待つ
        await asyncio.sleep(3)
        
        # 複数の可能なセレクタを試す
        content_selectors = [
            '#minuteFrame',  # iframe要素
            'iframe[name="minuteFrame"]',
            '#plain-minute',
            '.minute-content',
            '.meeting-content',
            '#meeting-text',
            'div[id*="minute"]',
            'div[class*="minute"]'
        ]
        
        content_found = False
        for selector in content_selectors:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                self.logger.info(f"Found content selector: {selector}")
                content_found = True
                break
            except:
                continue
        
        if not content_found:
            self.logger.warning("No standard content selectors found, checking for iframes...")
            
            # iframeをチェック
            iframes = await page.query_selector_all('iframe')
            if iframes:
                self.logger.info(f"Found {len(iframes)} iframes, may need to handle iframe content")
        
        # 最終的な待機時間
        await asyncio.sleep(2)
    
    async def _extract_iframe_content(self, page: Page) -> Optional[str]:
        """iframeからコンテンツを抽出"""
        try:
            # まずminuteFrameというiframeを探す
            iframe_element = await page.query_selector('iframe#minuteFrame, iframe[name="minuteFrame"]')
            if iframe_element:
                frame = await iframe_element.content_frame()
                if frame:
                    self.logger.info("Found minuteFrame iframe, extracting content...")
                    # iframe内のコンテンツを待つ
                    await asyncio.sleep(2)
                    return await frame.content()
            
            # 他のiframeも試す
            all_frames = page.frames
            for frame in all_frames:
                if frame != page.main_frame:
                    try:
                        frame_url = frame.url
                        self.logger.info(f"Checking frame: {frame_url}")
                        if 'minute' in frame_url.lower() or 'content' in frame_url.lower():
                            await asyncio.sleep(1)
                            return await frame.content()
                    except:
                        continue
            
            return None
        except Exception as e:
            self.logger.warning(f"Error extracting iframe content: {e}")
            return None
    
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
            '#outputframe-minute',
            '.minute-content',
            '.meeting-record',
            '.minute-body',
            '#minute-body',
            '.info-txt',  # kaigiroku.net特有のクラス
            'div[id*="minute"]',
            'div[class*="minute"]',
            '.content-main',
            '#content-main',
            'main',
            'article',
            '.document-content',
            '#document-content'
        ]
        
        for selector in content_selectors:
            elements = []
            if selector.startswith('#'):
                element = soup.find(id=selector[1:])
                if element:
                    elements = [element]
            elif selector.startswith('.'):
                elements = soup.find_all(class_=re.compile(selector[1:]))
            elif '[' in selector:
                # CSS attribute selector
                elements = soup.select(selector)
            else:
                element = soup.find(selector)
                if element:
                    elements = [element]
            
            for element in elements:
                # 不要な要素を削除
                for script in element.find_all(['script', 'style', 'noscript', 'button']):
                    script.decompose()
                
                # テキストを抽出
                text = element.get_text(separator='\n', strip=True)
                
                # 「印刷」や「文字拡大」などのボタンテキストを除去
                lines = text.split('\n')
                cleaned_lines = []
                for line in lines:
                    line = line.strip()
                    if line and not (
                        line == '印刷' or 
                        line == '文字拡大' or 
                        line == '文字縮小' or
                        line.startswith('「') and line.endswith('」ボタン')
                    ):
                        cleaned_lines.append(line)
                
                text = '\n'.join(cleaned_lines)
                
                if text and len(text) > 500:  # より多くのコンテンツを要求
                    self.logger.info(f"Found content with selector {selector}, length: {len(text)}")
                    return text
        
        # フォールバック: body全体から抽出
        body = soup.find('body')
        if body:
            # 不要な要素をより積極的に削除
            for tag in body.find_all(['script', 'style', 'noscript', 'header', 'footer', 'nav', 'button']):
                tag.decompose()
            
            # テーブル内のテキストも含める
            text = body.get_text(separator='\n', strip=True)
            
            # 議事録っぽいコンテンツを抽出
            lines = text.split('\n')
            content_lines = []
            for line in lines:
                line = line.strip()
                if line and (
                    '議' in line or '委員' in line or '市長' in line or 
                    '局長' in line or '部長' in line or '答弁' in line or 
                    '質問' in line or '会議' in line or '記録' in line or 
                    '令和' in line or '平成' in line or len(line) > 20
                ):
                    content_lines.append(line)
            
            if content_lines:
                return '\n'.join(content_lines)
        
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
    
    async def _find_pdf_download_url(self, page: Page) -> Optional[str]:
        """PDFダウンロードURLを見つける"""
        try:
            # ダウンロードボタンを探す
            selectors = [
                'a:has-text("PDF")',
                'a:has-text("ダウンロード")',
                'button:has-text("PDF")',
                'button:has-text("ダウンロード")',
                'a[href*=".pdf"]',
                'a[onclick*="download"]',
                'button[onclick*="download"]'
            ]
            
            for selector in selectors:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    # href属性をチェック
                    href = await element.get_attribute('href')
                    if href and '.pdf' in href:
                        if not href.startswith('http'):
                            base_url = page.url.split('?')[0]
                            base_url = '/'.join(base_url.split('/')[:-1])
                            href = f"{base_url}/{href}".replace('//', '/')
                        return href
                    
                    # onclick属性をチェック
                    onclick = await element.get_attribute('onclick')
                    if onclick:
                        # JavaScript関数からURLを抽出
                        import re
                        pdf_match = re.search(r'["\']([^"\']*\.pdf[^"\']*)["\']', onclick)
                        if pdf_match:
                            pdf_url = pdf_match.group(1)
                            if not pdf_url.startswith('http'):
                                base_url = page.url.split('?')[0]
                                base_url = '/'.join(base_url.split('/')[:-1])
                                pdf_url = f"{base_url}/{pdf_url}".replace('//', '/')
                            return pdf_url
            
            return None
        except Exception as e:
            self.logger.warning(f"Error finding PDF URL: {e}")
            return None
    
    async def _find_text_view_url(self, page: Page) -> Optional[str]:
        """テキスト表示用のURLを見つける"""
        try:
            # テキスト表示リンクを探す
            selectors = [
                'a:has-text("テキスト表示")',
                'a:has-text("本文表示")',
                'a:has-text("議事録表示")',
                'a[href*="TextView"]',
                'a[href*="text_view"]'
            ]
            
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    href = await element.get_attribute('href')
                    if href:
                        if not href.startswith('http'):
                            base_url = page.url.split('?')[0]
                            base_url = '/'.join(base_url.split('/')[:-1])
                            href = f"{base_url}/{href}".replace('//', '/')
                        return href
            
            return None
        except Exception as e:
            self.logger.warning(f"Error finding text view URL: {e}")
            return None
    
    async def _download_pdf_as_minutes(self, pdf_url: str, original_url: str) -> Optional[MinutesData]:
        """PDFをダウンロードして議事録データとして返す"""
        try:
            import aiohttp
            import os
            from datetime import datetime
            
            # PDFをダウンロード
            async with aiohttp.ClientSession() as session:
                async with session.get(pdf_url) as response:
                    if response.status == 200:
                        pdf_content = await response.read()
                        
                        # PDFを保存
                        parsed_url = urlparse(original_url)
                        params = parse_qs(parsed_url.query)
                        council_id = params.get('council_id', [''])[0]
                        schedule_id = params.get('schedule_id', [''])[0]
                        
                        pdf_filename = f"{council_id}_{schedule_id}.pdf"
                        pdf_path = os.path.join('data', 'scraped', pdf_filename)
                        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
                        
                        with open(pdf_path, 'wb') as f:
                            f.write(pdf_content)
                        
                        self.logger.info(f"PDF saved to: {pdf_path}")
                        
                        # PDFからテキストを抽出
                        try:
                            import pypdfium2 as pdfium
                            pdf = pdfium.PdfDocument(pdf_path)
                            text_content = ""
                            for page_num in range(len(pdf)):
                                page = pdf[page_num]
                                textpage = page.get_textpage()
                                text_content += textpage.get_text_bounded() + "\n"
                            pdf.close()
                        except:
                            text_content = f"PDF downloaded to {pdf_path}. Please process with PDF extraction tool."
                        
                        return MinutesData(
                            council_id=council_id,
                            schedule_id=schedule_id,
                            title=f"議事録 {council_id}_{schedule_id}",
                            date=None,
                            content=text_content,
                            speakers=[],
                            url=original_url,
                            pdf_url=pdf_url,
                            scraped_at=datetime.now()
                        )
            
            return None
        except Exception as e:
            self.logger.error(f"Error downloading PDF: {e}")
            return None