"""Tests for structlog and Sentry integration"""

from unittest.mock import patch

import structlog

from src.common.logging import SentryProcessor, get_logger, setup_logging


class TestSentryProcessor:
    """Test the SentryProcessor for structlog"""

    @patch("src.common.logging.SENTRY_AVAILABLE", False)
    def test_sentry_processor_when_sentry_not_available(self):
        """Test processor when Sentry is not available"""
        processor = SentryProcessor()
        event_dict = {"event": "test", "level": "error"}

        result = processor(None, "error", event_dict)

        assert result == event_dict

    @patch("src.common.logging.SENTRY_AVAILABLE", True)
    @patch("src.common.logging.sentry_sdk.capture_exception")
    def test_sentry_processor_with_exception(self, mock_capture_exception):
        """Test processor with exception info"""
        processor = SentryProcessor()
        exc_info = (ValueError, ValueError("test error"), None)
        event_dict = {"event": "Error occurred", "level": "error", "exc_info": exc_info}

        result = processor(None, "error", event_dict)

        assert result == event_dict
        # SentryProcessor should extract the exception instance from the tuple
        mock_capture_exception.assert_called_once_with(exc_info[1])

    @patch("src.common.logging.SENTRY_AVAILABLE", True)
    @patch("src.common.logging.sentry_sdk.capture_message")
    def test_sentry_processor_without_exception(self, mock_capture_message):
        """Test processor without exception info"""
        processor = SentryProcessor()
        event_dict = {
            "event": "Critical error message",
            "level": "critical",
            "user_id": "12345",
            "operation": "database_query",
        }

        result = processor(None, "critical", event_dict)

        assert result == event_dict
        mock_capture_message.assert_called_once()

        call_args = mock_capture_message.call_args
        assert call_args[0][0] == "Critical error message"
        assert call_args[1]["level"] == "critical"
        assert call_args[1]["extras"]["user_id"] == "12345"
        assert call_args[1]["extras"]["operation"] == "database_query"

    @patch("src.common.logging.SENTRY_AVAILABLE", True)
    @patch("src.common.logging.sentry_sdk.capture_message")
    def test_sentry_processor_info_level_not_sent(self, mock_capture_message):
        """Test that INFO level logs are not sent to Sentry"""
        processor = SentryProcessor()
        event_dict = {"event": "Info message", "level": "info"}

        result = processor(None, "info", event_dict)

        assert result == event_dict
        mock_capture_message.assert_not_called()

    @patch("src.common.logging.SENTRY_AVAILABLE", True)
    @patch("src.common.logging.sentry_sdk.capture_message")
    def test_sentry_processor_warning_level_not_sent(self, mock_capture_message):
        """Test that WARNING level logs are not sent to Sentry"""
        processor = SentryProcessor()
        event_dict = {"event": "Warning message", "level": "warning"}

        result = processor(None, "warning", event_dict)

        assert result == event_dict
        mock_capture_message.assert_not_called()


class TestLoggingWithSentryIntegration:
    """Test the full logging setup with Sentry integration"""

    @patch("src.common.logging.SENTRY_AVAILABLE", True)
    def test_setup_logging_with_sentry(self):
        """Test that Sentry processor is included in setup"""
        setup_logging(enable_sentry=True)

        # Get the current structlog configuration
        config = structlog.get_config()
        processors = config["processors"]

        # Check that SentryProcessor is in the list
        sentry_processor_found = any(isinstance(p, SentryProcessor) for p in processors)
        assert sentry_processor_found

    @patch("src.common.logging.SENTRY_AVAILABLE", True)
    def test_setup_logging_without_sentry(self):
        """Test that Sentry processor is not included when disabled"""
        setup_logging(enable_sentry=False)

        # Get the current structlog configuration
        config = structlog.get_config()
        processors = config["processors"]

        # Check that SentryProcessor is not in the list
        sentry_processor_found = any(isinstance(p, SentryProcessor) for p in processors)
        assert not sentry_processor_found

    @patch("src.common.logging.SENTRY_AVAILABLE", True)
    @patch("src.common.logging.sentry_sdk.capture_message")
    def test_error_logging_with_sentry(self, mock_capture_message):
        """Test that errors are sent to Sentry through structlog"""
        setup_logging(enable_sentry=True, json_format=False)

        logger = get_logger("test_module")
        logger.error("Test error message", extra_field="value")

        # Give time for async processing if any
        import time

        time.sleep(0.1)

        # Verify Sentry was called
        mock_capture_message.assert_called()
        call_args = mock_capture_message.call_args
        assert "Test error message" in str(call_args)

    @patch("src.common.logging.SENTRY_AVAILABLE", False)
    def test_setup_logging_when_sentry_not_available(self):
        """Test logging setup when Sentry SDK is not installed"""
        # Should not raise any errors
        setup_logging(enable_sentry=True)

        logger = get_logger("test_module")
        # Should work normally without Sentry
        logger.error("Test error without Sentry")
