"""
Polibase package

Political Activity Tracking Application for managing and analyzing
Japanese political activities.
"""

# Export exceptions for easier access - import from proper layers
# Domain layer
# Application layer
from .application.exceptions import (
    ConfigurationError,
    PDFProcessingError,
    ProcessingError,
    TextExtractionError,
)
from .application.exceptions import (
    InvalidConfigException as InvalidConfigError,
)
from .application.exceptions import (
    MissingConfigException as MissingConfigError,
)
from .domain.exceptions import PolibaseError

# Infrastructure layer
from .infrastructure.exceptions import (
    APIKeyError,
    ConnectionError,
    DatabaseError,
    IntegrityError,
    LLMError,
    PermissionError,
    RecordNotFoundError,
    SaveError,
    ScrapingError,
    StorageError,
    UpdateError,
)
from .infrastructure.exceptions import (
    DownloadException as DownloadError,
)
from .infrastructure.exceptions import (
    DuplicateRecordException as DuplicateRecordError,
)
from .infrastructure.exceptions import (
    ElementNotFoundException as ElementNotFoundError,
)
from .infrastructure.exceptions import (
    FileNotFoundException as FileNotFoundError,
)
from .infrastructure.exceptions import (
    PageLoadException as PageLoadError,
)
from .infrastructure.exceptions import (
    UploadException as UploadError,
)
from .infrastructure.exceptions import (
    URLException as URLError,
)

# Legacy aliases
ParsingError = TextExtractionError
ModelError = LLMError
TokenLimitError = LLMError
ResponseParsingError = LLMError
QueryError = DatabaseError
RepositoryError = SaveError
DeleteError = SaveError
ValidationError = ProcessingError
DataValidationError = ProcessingError
SchemaValidationError = ProcessingError

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
