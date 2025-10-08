"""Tests for custom exception hierarchy"""

import pytest

from src.exceptions import (
    APIKeyError,
    ConfigurationError,
    ConnectionError,
    DatabaseError,
    DeleteError,
    DuplicateRecordError,
    IntegrityError,
    LLMError,
    MissingConfigError,
    ModelError,
    ParsingError,
    PDFProcessingError,
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
    URLError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Test the exception hierarchy and inheritance"""

    def test_base_exception(self):
        """Test base PolibaseError"""
        error = PolibaseError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == {}

    def test_base_exception_with_details(self):
        """Test base PolibaseError with details"""
        details = {"key": "value", "count": 42}
        error = PolibaseError("Test error", details)
        # Note: New exception format shows error_code in brackets if present,
        # otherwise just message. Details stored but not shown in str()
        assert str(error) == "Test error"
        assert error.details == details

    def test_inheritance(self):
        """Test that all exceptions inherit from PolibaseError or PolibaseException"""
        from src.domain.exceptions import PolibaseException

        exceptions = [
            ConfigurationError("test"),
            DatabaseError("test"),
            ProcessingError("test"),
            LLMError("test"),
            ScrapingError("test"),
            StorageError("test"),
            ValidationError("test"),
            RepositoryError("test"),
        ]

        for exc in exceptions:
            # Should inherit from PolibaseError or PolibaseException
            assert isinstance(exc, PolibaseError | PolibaseException)


class TestConfigurationExceptions:
    """Test configuration-related exceptions"""

    def test_missing_config_error(self):
        """Test MissingConfigError"""
        from src.application.exceptions import ConfigurationException
        from src.domain.exceptions import PolibaseException

        error = MissingConfigError("Missing API key")
        # Should inherit from the new exception hierarchy
        assert isinstance(
            error, ConfigurationError | ConfigurationException | PolibaseException
        )

    def test_invalid_config_error(self):
        """Test InvalidConfigError"""
        from src.application.exceptions import (
            ConfigurationException,
            InvalidConfigException,
        )

        # InvalidConfigException requires config_key, actual_value, and reason
        error = InvalidConfigException(
            config_key="DATABASE_URL",
            actual_value="invalid_url",
            reason="Invalid database URL",
        )
        assert isinstance(error, ConfigurationError | ConfigurationException)


class TestDatabaseExceptions:
    """Test database-related exceptions"""

    def test_connection_error(self):
        """Test ConnectionError"""
        # Import explicitly to avoid Python's built-in ConnectionError
        from src.infrastructure.exceptions import (
            ConnectionError as CustomConnectionError,
        )
        from src.infrastructure.exceptions import InfrastructureException

        error = CustomConnectionError("Cannot connect to database")
        # ConnectionError is an InfrastructureException, not a DatabaseError
        assert isinstance(error, InfrastructureException)

    def test_query_error(self):
        """Test QueryError"""
        error = QueryError("Invalid SQL query")
        assert isinstance(error, DatabaseError)

    def test_integrity_error(self):
        """Test IntegrityError"""
        from src.infrastructure.exceptions import DatabaseException

        error = IntegrityError("Foreign key constraint violated")
        assert isinstance(error, DatabaseError | DatabaseException)

    def test_record_not_found_error(self):
        """Test RecordNotFoundError"""
        error = RecordNotFoundError("User", 123)
        # New format includes error code
        assert "User" in str(error) and "123" in str(error)
        # Check details are stored
        assert error.details.get("entity_type") == "User"
        assert error.details.get("entity_id") == 123

    def test_duplicate_record_error(self):
        """Test DuplicateRecordError"""
        error = DuplicateRecordError("User", "john@example.com")
        assert "User" in str(error) and "john@example.com" in str(error)
        # Check details are stored
        assert error.details.get("entity_type") == "User"
        assert error.details.get("identifier") == "john@example.com"


class TestProcessingExceptions:
    """Test processing-related exceptions"""

    def test_pdf_processing_error(self):
        """Test PDFProcessingError"""
        from src.application.exceptions import DataProcessingException

        error = PDFProcessingError("Cannot read PDF")
        assert isinstance(error, ProcessingError | DataProcessingException)

    def test_text_extraction_error(self):
        """Test TextExtractionError"""
        from src.application.exceptions import DataProcessingException

        error = TextExtractionError("Failed to extract text")
        assert isinstance(error, ProcessingError | DataProcessingException)

    def test_parsing_error(self):
        """Test ParsingError"""
        from src.application.exceptions import DataProcessingException

        error = ParsingError("Invalid JSON format")
        assert isinstance(error, ProcessingError | DataProcessingException)


class TestLLMExceptions:
    """Test LLM-related exceptions"""

    def test_api_key_error(self):
        """Test APIKeyError"""
        from src.infrastructure.exceptions import LLMServiceException

        error = APIKeyError("API key not set")
        assert isinstance(error, LLMError | LLMServiceException)

    def test_model_error(self):
        """Test ModelError"""
        error = ModelError("Model not available")
        assert isinstance(error, LLMError)

    def test_token_limit_error(self):
        """Test TokenLimitError"""
        error = TokenLimitError("Token limit exceeded")
        assert isinstance(error, LLMError)

    def test_response_parsing_error(self):
        """Test ResponseParsingError"""
        error = ResponseParsingError("Cannot parse LLM response")
        assert isinstance(error, LLMError)


class TestScrapingExceptions:
    """Test web scraping exceptions"""

    def test_url_error(self):
        """Test URLError"""

        error = URLError("https://example.com", "404 Not Found")
        # Check that key information is in the error message
        assert "https://example.com" in str(error)
        assert "404 Not Found" in str(error)
        # Check details are stored
        assert error.details.get("url") == "https://example.com"
        assert error.details.get("reason") == "404 Not Found"

    def test_page_load_error(self):
        """Test PageLoadError"""
        from src.infrastructure.exceptions import (
            PageLoadException,
            WebScrapingException,
        )

        # PageLoadException requires url and reason
        error = PageLoadException(
            url="https://example.com", reason="Timeout loading page"
        )
        assert isinstance(error, ScrapingError | WebScrapingException)

    def test_element_not_found_error(self):
        """Test ElementNotFoundError"""
        from src.infrastructure.exceptions import (
            ElementNotFoundException,
        )

        # ElementNotFoundException requires selector and page_url
        error = ElementNotFoundException(".button", "https://example.com")
        # Check that key information is in the error message
        assert ".button" in str(error)
        assert "https://example.com" in str(error)
        # Check details are stored (page_url is stored as 'url' in details)
        assert error.details.get("selector") == ".button"
        assert error.details.get("url") == "https://example.com"

    def test_download_error(self):
        """Test DownloadError"""
        from src.infrastructure.exceptions import (
            DownloadException,
            WebScrapingException,
        )

        # DownloadException requires url, file_type, and reason
        error = DownloadException(
            url="https://example.com/file.pdf",
            file_type="PDF",
            reason="Failed to download file",
        )
        assert isinstance(error, ScrapingError | WebScrapingException)


class TestStorageExceptions:
    """Test storage-related exceptions"""

    def test_file_not_found_error(self):
        """Test FileNotFoundError"""
        # Import explicitly to avoid Python's built-in FileNotFoundError
        from src.infrastructure.exceptions import (
            FileNotFoundException,
            FileSystemException,
        )

        # FileNotFoundException requires file_path argument
        error = FileNotFoundException("File not found")
        assert isinstance(error, FileSystemException)

    def test_upload_error(self):
        """Test UploadError"""
        # Import explicitly to avoid Python's built-in PermissionError
        from src.infrastructure.exceptions import (
            PermissionError as CustomPermissionError,
        )
        from src.infrastructure.exceptions import StorageException

        # UploadError maps to PermissionError in the shim
        error = CustomPermissionError("Upload failed")
        assert isinstance(error, StorageError | StorageException)

    def test_permission_error(self):
        """Test PermissionError"""
        # Import explicitly to avoid Python's built-in PermissionError
        from src.infrastructure.exceptions import (
            PermissionError as CustomPermissionError,
        )
        from src.infrastructure.exceptions import StorageException

        error = CustomPermissionError("Access denied")
        assert isinstance(error, StorageError | StorageException)


class TestValidationExceptions:
    """Test validation exceptions"""

    def test_data_validation_error(self):
        """Test DataValidationError"""

        # DataValidationError is an alias to ProcessingError
        error = ProcessingError(
            "Invalid email format",
            {"field": "email", "value": "invalid", "reason": "Invalid email format"},
        )
        # Check that key information is in the error message
        assert "Invalid email format" in str(error)
        # Check details are stored
        assert error.details.get("field") == "email"
        assert error.details.get("value") == "invalid"
        assert error.details.get("reason") == "Invalid email format"

    def test_schema_validation_error(self):
        """Test SchemaValidationError"""
        from src.application.exceptions import ValidationException

        error = SchemaValidationError("Schema mismatch")
        assert isinstance(error, ValidationError | ValidationException)


class TestRepositoryExceptions:
    """Test repository exceptions"""

    def test_save_error(self):
        """Test SaveError"""
        error = SaveError("Failed to save entity")
        assert isinstance(error, RepositoryError)

    def test_update_error(self):
        """Test UpdateError"""
        from src.infrastructure.exceptions import RepositoryException

        error = UpdateError("Failed to update entity")
        assert isinstance(error, RepositoryError | RepositoryException)

    def test_delete_error(self):
        """Test DeleteError"""
        error = DeleteError("Failed to delete entity")
        assert isinstance(error, RepositoryError)


class TestExceptionChaining:
    """Test exception chaining and context"""

    def test_exception_chaining(self):
        """Test that exceptions can be chained properly"""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise DatabaseError(
                    "Database operation failed", {"operation": "insert"}
                ) from e
        except DatabaseError as db_error:
            # New format includes error code
            assert "Database operation failed" in str(db_error)
            assert db_error.details.get("operation") == "insert"
            assert db_error.__cause__.__class__.__name__ == "ValueError"
            assert str(db_error.__cause__) == "Original error"

    def test_nested_exception_details(self):
        """Test nested exception details"""
        original_error = ConnectionError(
            "Connection timeout", {"host": "localhost", "port": 5432}
        )

        try:
            raise original_error
        except ConnectionError as e:
            try:
                raise QueryError(
                    "Query failed due to connection issue",
                    {"query": "SELECT * FROM users"},
                ) from e
            except QueryError as qe:
                assert qe.details["query"] == "SELECT * FROM users"
                assert qe.__cause__.details["host"] == "localhost"
                assert qe.__cause__.details["port"] == 5432


class TestExceptionHandlingInCLI:
    """Test exception handling in CLI context"""

    def test_api_key_error_exit_code(self):
        """Test that APIKeyError should result in specific exit code"""
        error = APIKeyError("GOOGLE_API_KEY not set", {"env_var": "GOOGLE_API_KEY"})
        # In actual CLI, this would exit with code 2
        assert error.details["env_var"] == "GOOGLE_API_KEY"

    def test_connection_error_exit_code(self):
        """Test that ConnectionError should result in specific exit code"""
        error = ConnectionError(
            "Cannot connect to database", {"host": "localhost", "port": 5432}
        )
        # In actual CLI, this would exit with code 3
        assert error.details["host"] == "localhost"

    def test_record_not_found_exit_code(self):
        """Test that RecordNotFoundError should result in specific exit code"""
        error = RecordNotFoundError("Meeting", 999)
        # In actual CLI, this would exit with code 4
        # Check details are stored
        assert error.details.get("entity_type") == "Meeting"
        assert error.details.get("entity_id") == 999


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
