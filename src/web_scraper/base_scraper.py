"""Base scraper class for council minutes extraction"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional
import logging


@dataclass
class MinutesData:
    """議事録データモデル"""
    council_id: str
    schedule_id: str
    title: str
    date: datetime
    content: str
    speakers: List[Dict[str, str]]  # [{"name": "発言者名", "content": "発言内容"}]
    url: str
    scraped_at: datetime
    pdf_url: Optional[str] = None
    
    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "council_id": self.council_id,
            "schedule_id": self.schedule_id,
            "title": self.title,
            "date": self.date.isoformat() if self.date else None,
            "content": self.content,
            "speakers": self.speakers,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None
        }


class BaseScraper(ABC):
    """議事録スクレーパーの基底クラス"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def fetch_minutes(self, url: str) -> Optional[MinutesData]:
        """指定されたURLから議事録を取得"""
        pass
    
    @abstractmethod
    async def extract_minutes_text(self, html_content: str) -> str:
        """HTMLから議事録テキストを抽出"""
        pass
    
    @abstractmethod
    async def extract_speakers(self, html_content: str) -> List[Dict[str, str]]:
        """HTMLから発言者情報を抽出"""
        pass
    
    def parse_japanese_date(self, date_str: str) -> Optional[datetime]:
        """日本語の日付文字列をパース"""
        import re
        from datetime import datetime
        
        # 令和6年12月20日 のようなパターン
        match = re.match(r'令和(\d+)年(\d+)月(\d+)日', date_str)
        if match:
            reiwa_year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            year = 2018 + reiwa_year  # 令和元年 = 2019
            return datetime(year, month, day)
        
        # 平成31年4月1日 のようなパターン
        match = re.match(r'平成(\d+)年(\d+)月(\d+)日', date_str)
        if match:
            heisei_year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            year = 1988 + heisei_year  # 平成元年 = 1989
            return datetime(year, month, day)
        
        # 2024年12月20日 のようなパターン
        match = re.match(r'(\d{4})年(\d+)月(\d+)日', date_str)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))
            return datetime(year, month, day)
        
        return None