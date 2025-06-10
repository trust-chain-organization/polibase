"""
Polibase package

Political Activity Tracking Application for managing and analyzing
Japanese political activities.
"""

# Export exceptions for easier access
from .exceptions import (
    APIKeyError,
    ConfigurationError,
    ConnectionError,
    DatabaseError,
    DataValidationError,
    DeleteError,
    DownloadError,
    DuplicateRecordError,
    ElementNotFoundError,
    FileNotFoundError,
    IntegrityError,
    InvalidConfigError,
    LLMError,
    MissingConfigError,
    ModelError,
    PageLoadError,
    ParsingError,
    PDFProcessingError,
    PermissionError,
    PolibaseError,
    ProcessingError,
    QueryError,
    RecordNotFoundError,
    RepositoryError,
    ResponseParsingError,
    SaveError,
    SchemaValidationError,
    ScrapingError,
    StorageError,
    TextExtractionError,
    TokenLimitError,
    UpdateError,
    UploadError,
    URLError,
    ValidationError,
)

__all__ = [
    # Base exception
    "PolibaseError",
    # Configuration
    "ConfigurationError",
    "MissingConfigError",
    "InvalidConfigError",
    # Database
    "DatabaseError",
    "ConnectionError",
    "QueryError",
    "IntegrityError",
    "RecordNotFoundError",
    "DuplicateRecordError",
    # Processing
    "ProcessingError",
    "PDFProcessingError",
    "TextExtractionError",
    "ParsingError",
    # LLM/AI
    "LLMError",
    "APIKeyError",
    "ModelError",
    "TokenLimitError",
    "ResponseParsingError",
    # Web Scraping
    "ScrapingError",
    "URLError",
    "PageLoadError",
    "ElementNotFoundError",
    "DownloadError",
    # Storage
    "StorageError",
    "FileNotFoundError",
    "UploadError",
    "PermissionError",
    # Validation
    "ValidationError",
    "DataValidationError",
    "SchemaValidationError",
    # Repository
    "RepositoryError",
    "SaveError",
    "UpdateError",
    "DeleteError",
]

__version__ = "0.1.0"
