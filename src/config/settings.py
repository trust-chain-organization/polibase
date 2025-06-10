"""Centralized configuration management using environment variables

Provides a single source of truth for application configuration with
validation and type safety.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from ..exceptions import ConfigurationError, InvalidConfigError, MissingConfigError

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables"""

    def __init__(self) -> None:
        """Initialize settings from environment variables

        Raises:
            InvalidConfigError: If configuration values are invalid
        """
        # Database configuration
        self.database_url: str = os.getenv(
            "DATABASE_URL",
            "postgresql://polibase_user:polibase_password@localhost:5432/polibase_db",
        )

        # API Keys
        self.google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
        self.langchain_api_key: str = os.getenv("LANGCHAIN_API_KEY", "")
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")

        # LangChain configuration
        self.langchain_tracing_v2: bool = (
            os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        )
        self.langchain_endpoint: str = os.getenv("LANGCHAIN_ENDPOINT", "")
        self.langchain_project: str = os.getenv("LANGCHAIN_PROJECT", "")

        # Application paths
        self.default_pdf_path: str = os.getenv("DEFAULT_PDF_PATH", "data/minutes.pdf")
        self.output_dir: str = os.getenv("OUTPUT_DIR", "data/output")

        # LLM Model settings
        self.llm_model: str = os.getenv("LLM_MODEL", "gemini-2.0-flash")

        # Parse temperature with validation
        try:
            self.llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))
            if not 0.0 <= self.llm_temperature <= 2.0:
                raise ValueError("Temperature must be between 0.0 and 2.0")
        except ValueError as e:
            logger.error(f"Invalid LLM_TEMPERATURE value: {e}")
            raise InvalidConfigError(
                "Invalid LLM_TEMPERATURE configuration",
                {"value": os.getenv("LLM_TEMPERATURE"), "error": str(e)},
            ) from e

        # GCS Configuration
        self.gcs_bucket_name: str = os.getenv(
            "GCS_BUCKET_NAME", "polibase-scraped-minutes"
        )
        self.gcs_project_id: str | None = os.getenv("GCS_PROJECT_ID")
        self.gcs_upload_enabled: bool = (
            os.getenv("GCS_UPLOAD_ENABLED", "false").lower() == "true"
        )

        # Timeout settings (in seconds)
        self.web_scraper_timeout: int = int(os.getenv("WEB_SCRAPER_TIMEOUT", "60"))
        self.pdf_download_timeout: int = int(os.getenv("PDF_DOWNLOAD_TIMEOUT", "120"))
        self.page_load_timeout: int = int(os.getenv("PAGE_LOAD_TIMEOUT", "30"))
        self.selector_wait_timeout: int = int(os.getenv("SELECTOR_WAIT_TIMEOUT", "10"))

        # Validate paths exist
        self._validate_paths()

    def validate(self) -> None:
        """Validate required settings

        Raises:
            MissingConfigError: If required configuration is missing
            InvalidConfigError: If configuration is invalid
        """
        # Validate database URL
        if not self.database_url:
            raise MissingConfigError(
                "DATABASE_URL is required", {"env_var": "DATABASE_URL"}
            )

        if not self.database_url.startswith(("postgresql://", "postgres://")):
            raise InvalidConfigError(
                "DATABASE_URL must be a valid PostgreSQL connection string",
                {"current_value": self.database_url[:30] + "..."},
            )

        # Warn about missing API keys (not required for all operations)
        if not self.google_api_key:
            logger.warning(
                "GOOGLE_API_KEY is not set. LLM features will not work. "
                "Please set it in your .env file or environment variables."
            )

    def _validate_paths(self) -> None:
        """Validate configured paths"""
        # Create output directory if it doesn't exist
        output_path = Path(self.output_dir)
        try:
            output_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create output directory: {e}")
            raise InvalidConfigError(
                f"Invalid output directory: {self.output_dir}",
                {"path": self.output_dir, "error": str(e)},
            ) from e

    def get_database_url(self) -> str:
        """Get the appropriate database URL based on environment

        Returns:
            Database connection URL
        """
        # Check if running in Docker
        if os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER"):
            # Use Docker service name for host
            if "localhost" in self.database_url:
                return self.database_url.replace("localhost", "postgres")
        return self.database_url

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"

    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled"""
        return os.getenv("DEBUG", "false").lower() == "true"

    @property
    def log_level(self) -> str:
        """Get the logging level"""
        if self.debug:
            return "DEBUG"
        return os.getenv("LOG_LEVEL", "INFO").upper()

    def get_required(self, key: str) -> str:
        """Get a required configuration value

        Args:
            key: Configuration attribute name

        Returns:
            Configuration value

        Raises:
            MissingConfigError: If configuration is not set or empty
        """
        value = getattr(self, key, None)
        if not value:
            raise MissingConfigError(
                f"Required configuration '{key}' is not set", {"key": key}
            )
        return value


# Global settings instance
try:
    settings = Settings()
    logger.info("Settings loaded successfully")
except Exception as e:
    logger.error(f"Failed to load settings: {e}")
    # Create a minimal settings object to avoid import errors
    settings = None  # type: ignore


def get_settings() -> Settings:
    """Get the global settings instance

    Returns:
        Global Settings instance

    Raises:
        ConfigurationError: If settings failed to load
    """
    if settings is None:
        raise ConfigurationError(
            "Settings failed to initialize. Check your environment configuration."
        )
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment

    Returns:
        New Settings instance

    Raises:
        ConfigurationError: If settings fail to load
    """
    global settings
    try:
        settings = Settings()
        logger.info("Settings reloaded successfully")
        return settings
    except Exception as e:
        logger.error(f"Failed to reload settings: {e}")
        raise ConfigurationError("Failed to reload settings", {"error": str(e)}) from e
