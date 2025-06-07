"""Base scraper class for council minutes extraction"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional
import logging

from .models import MinutesData, SpeakerData
from .extractors import DateParser


class BaseScraper(ABC):
    """議事録スクレーパーの基底クラス"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.date_parser = DateParser(logger=self.logger)
    
    @abstractmethod
    async def fetch_minutes(self, url: str) -> Optional[MinutesData]:
        """指定されたURLから議事録を取得"""
        pass
    
    @abstractmethod
    async def extract_minutes_text(self, html_content: str) -> str:
        """HTMLから議事録テキストを抽出"""
        pass
    
    @abstractmethod
    async def extract_speakers(self, html_content: str) -> List[SpeakerData]:
        """HTMLから発言者情報を抽出"""
        pass
    
    def parse_japanese_date(self, date_str: str) -> Optional[datetime]:
        """日本語の日付文字列をパース"""
        return self.date_parser.parse(date_str)