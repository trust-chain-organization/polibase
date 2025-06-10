"""Web scraper custom exceptions"""


class ScraperError(Exception):
    """Base exception for web scraper"""

    pass


class ScraperConnectionError(ScraperError):
    """Raised when connection to the website fails"""

    pass


class ScraperParseError(ScraperError):
    """Raised when parsing content fails"""

    pass


class ScraperTimeoutError(ScraperError):
    """Raised when scraping operation times out"""

    pass


class PDFDownloadError(ScraperError):
    """Raised when PDF download fails"""

    pass


class PDFExtractionError(ScraperError):
    """Raised when PDF text extraction fails"""

    pass


class CacheError(ScraperError):
    """Raised when cache operations fail"""

    pass


class GCSUploadError(ScraperError):
    """Raised when GCS upload fails"""

    pass
