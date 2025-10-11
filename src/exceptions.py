"""
DEPRECATED: This module is deprecated and will be removed in a future version.

Please import exceptions from their respective layers:
- Domain exceptions: from src.domain.exceptions import ...
- Application exceptions: from src.application.exceptions import ...
- Infrastructure exceptions: from src.infrastructure.exceptions import ...

This file now serves as a compatibility shim for backward compatibility.
"""

import warnings

# Show deprecation warning when this module is imported
warnings.warn(
    "src.exceptions is deprecated. "
    "Import exceptions from their respective layers: "
    "domain.exceptions, application.exceptions, or infrastructure.exceptions",
    DeprecationWarning,
    stacklevel=2,
)

# Domain layer exceptions
# Application layer exceptions
from src.application.exceptions import (  # noqa: E402, F401
    ConfigurationError,
    ConfigurationException,
    InvalidConfigException,
    MissingConfigException,
    PDFProcessingError,
    ProcessingError,
    TextExtractionError,
)
from src.domain.exceptions import (  # noqa: E402, F401
    PolibaseError,
    PolibaseException,
)

# Infrastructure layer exceptions
from src.infrastructure.exceptions import (  # noqa: E402, F401
    APIKeyError,
    ConnectionError,
    DatabaseError,
    DownloadException,
    DuplicateRecordException,
    ElementNotFoundException,
    FileNotFoundException,
    IntegrityError,
    LLMError,
    PageLoadException,
    PermissionError,
    RecordNotFoundError,
    SaveError,
    ScrapingError,
    StorageError,
    UpdateError,
    UploadException,
    URLException,
)

# Backward compatibility aliases for infrastructure exceptions
DownloadError = DownloadException
ElementNotFoundError = ElementNotFoundException
PageLoadError = PageLoadException
URLError = URLException
DuplicateRecordError = DuplicateRecordException

# Backward compatibility aliases for application exceptions
MissingConfigError = MissingConfigException
InvalidConfigError = InvalidConfigException

# Legacy type aliases that were incorrectly in root exceptions
ParsingError = TextExtractionError  # Map to closest equivalent
ModelError = LLMError  # Map to closest equivalent
TokenLimitError = LLMError  # Map to closest equivalent
ResponseParsingError = LLMError  # Map to closest equivalent
UploadError = PermissionError  # Map to closest equivalent
FileNotFoundError = FileNotFoundException
QueryError = DatabaseError  # Map to base database error
RepositoryError = SaveError  # Map to closest equivalent
DeleteError = SaveError  # Map to general repository error
ValidationError = ProcessingError  # Map to closest equivalent
DataValidationError = ProcessingError  # Map to closest equivalent
SchemaValidationError = ProcessingError  # Map to closest equivalent
# StorageError is imported from infrastructure.exceptions

__all__ = [
    # Base exceptions
    "PolibaseError",
    "PolibaseException",
    # Application layer
    "ConfigurationError",
    "ConfigurationException",
    "InvalidConfigError",
    "InvalidConfigException",
    "MissingConfigError",
    "MissingConfigException",
    "PDFProcessingError",
    "ProcessingError",
    "TextExtractionError",
    # Infrastructure layer
    "APIKeyError",
    "ConnectionError",
    "DatabaseError",
    "DownloadError",
    "DownloadException",
    "DuplicateRecordError",
    "DuplicateRecordException",
    "ElementNotFoundError",
    "ElementNotFoundException",
    "FileNotFoundError",
    "FileNotFoundException",
    "IntegrityError",
    "LLMError",
    "PageLoadError",
    "PageLoadException",
    "PermissionError",
    "RecordNotFoundError",
    "SaveError",
    "ScrapingError",
    "UpdateError",
    "URLError",
    "URLException",
    # Legacy aliases
    "ParsingError",
    "ModelError",
    "TokenLimitError",
    "ResponseParsingError",
    "UploadError",
    "QueryError",
    "RepositoryError",
    "DeleteError",
    "ValidationError",
    "DataValidationError",
    "SchemaValidationError",
    "StorageError",
]
