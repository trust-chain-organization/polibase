"""議事録スクレーパーサービス"""
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import logging

from .base_scraper import MinutesData
from .kaigiroku_net_scraper import KaigirokuNetScraper


class ScraperService:
    """議事録スクレーパーの統合サービス"""
    
    def __init__(self, cache_dir: str = "./cache/minutes"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    async def fetch_from_url(self, url: str, use_cache: bool = True) -> Optional[MinutesData]:
        """URLから議事録を取得"""
        # キャッシュチェック
        if use_cache:
            cached = self._get_from_cache(url)
            if cached:
                self.logger.info(f"Using cached data for {url}")
                return cached
        
        # URLから適切なスクレーパーを選択
        scraper = self._get_scraper_for_url(url)
        if not scraper:
            self.logger.error(f"No scraper available for URL: {url}")
            return None
        
        # スクレープ実行
        self.logger.info(f"Fetching minutes from {url}")
        try:
            minutes = await scraper.fetch_minutes(url)
            if minutes:
                # キャッシュに保存
                self._save_to_cache(url, minutes)
                return minutes
        except Exception as e:
            self.logger.error(f"Error fetching minutes: {e}")
        
        return None
    
    async def fetch_multiple(self, urls: List[str], max_concurrent: int = 3) -> List[Optional[MinutesData]]:
        """複数のURLから並列で議事録を取得"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_with_limit(url: str) -> Optional[MinutesData]:
            async with semaphore:
                return await self.fetch_from_url(url)
        
        tasks = [fetch_with_limit(url) for url in urls]
        return await asyncio.gather(*tasks)
    
    def _get_scraper_for_url(self, url: str) -> Optional[object]:
        """URLに基づいて適切なスクレーパーを選択"""
        # kaigiroku.netシステムの場合
        if "kaigiroku.net/tenant/" in url:
            return KaigirokuNetScraper()
        
        # 今後、他の議事録システムのスクレーパーをここに追加
        # 例: 独自システムを使う自治体など
        
        return None
    
    def _get_cache_key(self, url: str) -> str:
        """URLからキャッシュキーを生成"""
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_from_cache(self, url: str) -> Optional[MinutesData]:
        """キャッシュから取得"""
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # MinutesDataオブジェクトに変換
                data['date'] = datetime.fromisoformat(data['date']) if data.get('date') else None
                data['scraped_at'] = datetime.fromisoformat(data['scraped_at']) if data.get('scraped_at') else None
                
                return MinutesData(**data)
            except Exception as e:
                self.logger.warning(f"Failed to load cache for {url}: {e}")
        
        return None
    
    def _save_to_cache(self, url: str, minutes: MinutesData):
        """キャッシュに保存"""
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(minutes.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save cache for {url}: {e}")
    
    def export_to_pdf(self, minutes: MinutesData, output_path: str) -> bool:
        """議事録をPDFにエクスポート"""
        # TODO: PDFエクスポート機能の実装
        # reportlabやweasyprint等を使用
        pass
    
    def export_to_text(self, minutes: MinutesData, output_path: str) -> bool:
        """議事録をテキストファイルにエクスポート"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"タイトル: {minutes.title}\n")
                f.write(f"日付: {minutes.date.strftime('%Y年%m月%d日') if minutes.date else '不明'}\n")
                f.write(f"URL: {minutes.url}\n")
                f.write("\n" + "="*50 + "\n\n")
                f.write(minutes.content)
                
                if minutes.speakers:
                    f.write("\n\n" + "="*50 + "\n")
                    f.write("発言者一覧:\n\n")
                    for speaker in minutes.speakers:
                        f.write(f"【{speaker['name']}】\n")
                        f.write(f"{speaker['content']}\n\n")
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to export to text: {e}")
            return False