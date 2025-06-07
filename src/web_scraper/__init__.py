"""Web scraper module for extracting minutes from various council websites"""
from .base_scraper import BaseScraper
from .models import MinutesData, SpeakerData
from .kaigiroku_net_scraper import KaigirokuNetScraper
from .scraper_service import ScraperService
from .exceptions import (
    ScraperException,
    ScraperConnectionError,
    ScraperParseError,
    ScraperTimeoutError,
    PDFDownloadError,
    PDFExtractionError,
    CacheError,
    GCSUploadError
)

__all__ = [
    # Base classes
    "BaseScraper",
    
    # Models
    "MinutesData",
    "SpeakerData",
    
    # Scrapers
    "KaigirokuNetScraper",
    "ScraperService",
    
    # Exceptions
    "ScraperException",
    "ScraperConnectionError",
    "ScraperParseError",
    "ScraperTimeoutError",
    "PDFDownloadError",
    "PDFExtractionError",
    "CacheError",
    "GCSUploadError"
]