"""Tests for custom exception hierarchy"""

import pytest

from src.exceptions import (
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
        assert str(error) == "Test error | Details: {'key': 'value', 'count': 42}"
        assert error.details == details

    def test_inheritance(self):
        """Test that all exceptions inherit from PolibaseError"""
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
            assert isinstance(exc, PolibaseError)


class TestConfigurationExceptions:
    """Test configuration-related exceptions"""

    def test_missing_config_error(self):
        """Test MissingConfigError"""
        error = MissingConfigError("Missing API key")
        assert isinstance(error, ConfigurationError)
        assert isinstance(error, PolibaseError)

    def test_invalid_config_error(self):
        """Test InvalidConfigError"""
        error = InvalidConfigError("Invalid database URL")
        assert isinstance(error, ConfigurationError)


class TestDatabaseExceptions:
    """Test database-related exceptions"""

    def test_connection_error(self):
        """Test ConnectionError"""
        error = ConnectionError("Cannot connect to database")
        assert isinstance(error, DatabaseError)

    def test_query_error(self):
        """Test QueryError"""
        error = QueryError("Invalid SQL query")
        assert isinstance(error, DatabaseError)

    def test_integrity_error(self):
        """Test IntegrityError"""
        error = IntegrityError("Foreign key constraint violated")
        assert isinstance(error, DatabaseError)

    def test_record_not_found_error(self):
        """Test RecordNotFoundError"""
        error = RecordNotFoundError("User", 123)
        assert (
            str(error) == "User with id 123 not found | "
            "Details: {'entity_type': 'User', 'entity_id': 123}"
        )
        assert error.entity_type == "User"
        assert error.entity_id == 123

    def test_duplicate_record_error(self):
        """Test DuplicateRecordError"""
        error = DuplicateRecordError("User", "john@example.com")
        assert "Duplicate User found: john@example.com" in str(error)
        assert error.entity_type == "User"
        assert error.identifier == "john@example.com"


class TestProcessingExceptions:
    """Test processing-related exceptions"""

    def test_pdf_processing_error(self):
        """Test PDFProcessingError"""
        error = PDFProcessingError("Cannot read PDF")
        assert isinstance(error, ProcessingError)

    def test_text_extraction_error(self):
        """Test TextExtractionError"""
        error = TextExtractionError("Failed to extract text")
        assert isinstance(error, ProcessingError)

    def test_parsing_error(self):
        """Test ParsingError"""
        error = ParsingError("Invalid JSON format")
        assert isinstance(error, ProcessingError)


class TestLLMExceptions:
    """Test LLM-related exceptions"""

    def test_api_key_error(self):
        """Test APIKeyError"""
        error = APIKeyError("API key not set")
        assert isinstance(error, LLMError)

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
        assert (
            "Failed to access URL: https://example.com. Reason: 404 Not Found"
            in str(error)
        )
        assert error.url == "https://example.com"
        assert error.reason == "404 Not Found"

    def test_page_load_error(self):
        """Test PageLoadError"""
        error = PageLoadError("Timeout loading page")
        assert isinstance(error, ScrapingError)

    def test_element_not_found_error(self):
        """Test ElementNotFoundError"""
        error = ElementNotFoundError(".button", "https://example.com")
        assert "Element '.button' not found on page: https://example.com" in str(error)
        assert error.selector == ".button"
        assert error.page_url == "https://example.com"

    def test_download_error(self):
        """Test DownloadError"""
        error = DownloadError("Failed to download file")
        assert isinstance(error, ScrapingError)


class TestStorageExceptions:
    """Test storage-related exceptions"""

    def test_file_not_found_error(self):
        """Test FileNotFoundError"""
        error = FileNotFoundError("File not found")
        assert isinstance(error, StorageError)

    def test_upload_error(self):
        """Test UploadError"""
        error = UploadError("Upload failed")
        assert isinstance(error, StorageError)

    def test_permission_error(self):
        """Test PermissionError"""
        error = PermissionError("Access denied")
        assert isinstance(error, StorageError)


class TestValidationExceptions:
    """Test validation exceptions"""

    def test_data_validation_error(self):
        """Test DataValidationError"""
        error = DataValidationError("email", "invalid", "Invalid email format")
        assert "Validation failed for field 'email': Invalid email format" in str(error)
        assert error.field == "email"
        assert error.value == "invalid"
        assert error.reason == "Invalid email format"

    def test_schema_validation_error(self):
        """Test SchemaValidationError"""
        error = SchemaValidationError("Schema mismatch")
        assert isinstance(error, ValidationError)


class TestRepositoryExceptions:
    """Test repository exceptions"""

    def test_save_error(self):
        """Test SaveError"""
        error = SaveError("Failed to save entity")
        assert isinstance(error, RepositoryError)

    def test_update_error(self):
        """Test UpdateError"""
        error = UpdateError("Failed to update entity")
        assert isinstance(error, RepositoryError)

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
            assert (
                str(db_error)
                == "Database operation failed | Details: {'operation': 'insert'}"
            )
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
        assert error.entity_type == "Meeting"
        assert error.entity_id == 999


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
