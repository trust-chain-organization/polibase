"""
Polibase package

Political Activity Tracking Application for managing and analyzing Japanese political activities.
"""

# Export exceptions for easier access
from .exceptions import (
    PolibaseException,
    ConfigurationError,
    MissingConfigError,
    InvalidConfigError,
    DatabaseError,
    ConnectionError,
    QueryError,
    IntegrityError,
    RecordNotFoundError,
    DuplicateRecordError,
    ProcessingError,
    PDFProcessingError,
    TextExtractionError,
    ParsingError,
    LLMError,
    APIKeyError,
    ModelError,
    TokenLimitError,
    ResponseParsingError,
    ScrapingError,
    URLError,
    PageLoadError,
    ElementNotFoundError,
    DownloadError,
    StorageError,
    FileNotFoundError,
    UploadError,
    PermissionError,
    ValidationError,
    DataValidationError,
    SchemaValidationError,
    RepositoryError,
    SaveError,
    UpdateError,
    DeleteError,
)

__all__ = [
    # Base exception
    'PolibaseException',
    
    # Configuration
    'ConfigurationError',
    'MissingConfigError',
    'InvalidConfigError',
    
    # Database
    'DatabaseError',
    'ConnectionError',
    'QueryError',
    'IntegrityError',
    'RecordNotFoundError',
    'DuplicateRecordError',
    
    # Processing
    'ProcessingError',
    'PDFProcessingError',
    'TextExtractionError',
    'ParsingError',
    
    # LLM/AI
    'LLMError',
    'APIKeyError',
    'ModelError',
    'TokenLimitError',
    'ResponseParsingError',
    
    # Web Scraping
    'ScrapingError',
    'URLError',
    'PageLoadError',
    'ElementNotFoundError',
    'DownloadError',
    
    # Storage
    'StorageError',
    'FileNotFoundError',
    'UploadError',
    'PermissionError',
    
    # Validation
    'ValidationError',
    'DataValidationError',
    'SchemaValidationError',
    
    # Repository
    'RepositoryError',
    'SaveError',
    'UpdateError',
    'DeleteError',
]

__version__ = '0.1.0'