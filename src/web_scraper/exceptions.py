"""Web scraper custom exceptions"""


class ScraperException(Exception):
    """Base exception for web scraper"""
    pass


class ScraperConnectionError(ScraperException):
    """Raised when connection to the website fails"""
    pass


class ScraperParseError(ScraperException):
    """Raised when parsing content fails"""
    pass


class ScraperTimeoutError(ScraperException):
    """Raised when scraping operation times out"""
    pass


class PDFDownloadError(ScraperException):
    """Raised when PDF download fails"""
    pass


class PDFExtractionError(ScraperException):
    """Raised when PDF text extraction fails"""
    pass


class CacheError(ScraperException):
    """Raised when cache operations fail"""
    pass


class GCSUploadError(ScraperException):
    """Raised when GCS upload fails"""
    pass