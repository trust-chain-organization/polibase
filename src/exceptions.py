"""
Polibase custom exception hierarchy

This module defines domain-specific exceptions for different parts of the application.
"""

from typing import Any


class PolibaseError(Exception):
    """Base exception for all Polibase errors"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# Configuration Exceptions
class ConfigurationError(PolibaseError):
    """Raised when there's a configuration error"""

    pass


class MissingConfigError(ConfigurationError):
    """Raised when required configuration is missing"""

    pass


class InvalidConfigError(ConfigurationError):
    """Raised when configuration is invalid"""

    pass


# Database Exceptions
class DatabaseError(PolibaseError):
    """Base exception for database-related errors"""

    pass


class ConnectionError(DatabaseError):
    """Raised when database connection fails"""

    pass


class QueryError(DatabaseError):
    """Raised when database query fails"""

    pass


class IntegrityError(DatabaseError):
    """Raised when database integrity constraint is violated"""

    pass


class RecordNotFoundError(DatabaseError):
    """Raised when a database record is not found"""

    def __init__(self, entity_type: str, entity_id: Any):
        super().__init__(
            f"{entity_type} with id {entity_id} not found",
            {"entity_type": entity_type, "entity_id": entity_id},
        )
        self.entity_type = entity_type
        self.entity_id = entity_id


class DuplicateRecordError(DatabaseError):
    """Raised when attempting to create a duplicate record"""

    def __init__(self, entity_type: str, identifier: Any):
        super().__init__(
            f"Duplicate {entity_type} found: {identifier}",
            {"entity_type": entity_type, "identifier": identifier},
        )
        self.entity_type = entity_type
        self.identifier = identifier


# Processing Exceptions
class ProcessingError(PolibaseError):
    """Base exception for processing errors"""

    pass


class PDFProcessingError(ProcessingError):
    """Raised when PDF processing fails"""

    pass


class TextExtractionError(ProcessingError):
    """Raised when text extraction fails"""

    pass


class ParsingError(ProcessingError):
    """Raised when parsing fails"""

    pass


# LLM/AI Exceptions
class LLMError(PolibaseError):
    """Base exception for LLM-related errors"""

    pass


class APIKeyError(LLMError):
    """Raised when API key is missing or invalid"""

    pass


class ModelError(LLMError):
    """Raised when LLM model encounters an error"""

    pass


class TokenLimitError(LLMError):
    """Raised when token limit is exceeded"""

    pass


class ResponseParsingError(LLMError):
    """Raised when LLM response parsing fails"""

    pass


# Web Scraping Exceptions
class ScrapingError(PolibaseError):
    """Base exception for web scraping errors"""

    pass


class URLError(ScrapingError):
    """Raised when URL is invalid or inaccessible"""

    def __init__(self, url: str, reason: str):
        super().__init__(
            f"Failed to access URL: {url}. Reason: {reason}",
            {"url": url, "reason": reason},
        )
        self.url = url
        self.reason = reason


class PageLoadError(ScrapingError):
    """Raised when page fails to load"""

    pass


class ElementNotFoundError(ScrapingError):
    """Raised when expected element is not found on page"""

    def __init__(self, selector: str, page_url: str):
        super().__init__(
            f"Element '{selector}' not found on page: {page_url}",
            {"selector": selector, "page_url": page_url},
        )
        self.selector = selector
        self.page_url = page_url


class DownloadError(ScrapingError):
    """Raised when file download fails"""

    pass


# Storage Exceptions
class StorageError(PolibaseError):
    """Base exception for storage-related errors"""

    pass


class FileNotFoundError(StorageError):
    """Raised when file is not found"""

    pass


class UploadError(StorageError):
    """Raised when file upload fails"""

    pass


class PermissionError(StorageError):
    """Raised when storage permission is denied"""

    pass


# Validation Exceptions
class ValidationError(PolibaseError):
    """Base exception for validation errors"""

    pass


class DataValidationError(ValidationError):
    """Raised when data validation fails"""

    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            f"Validation failed for field '{field}': {reason}",
            {"field": field, "value": value, "reason": reason},
        )
        self.field = field
        self.value = value
        self.reason = reason


class SchemaValidationError(ValidationError):
    """Raised when schema validation fails"""

    pass


# Repository Exceptions
class RepositoryError(PolibaseError):
    """Base exception for repository errors"""

    pass


class SaveError(RepositoryError):
    """Raised when saving to repository fails"""

    pass


class UpdateError(RepositoryError):
    """Raised when updating in repository fails"""

    pass


class DeleteError(RepositoryError):
    """Raised when deleting from repository fails"""

    pass
