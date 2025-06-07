"""
Configuration module for Polibase application

Loads and validates environment variables with proper type hints and error handling.
"""
import os
from typing import Optional
from dotenv import load_dotenv

from ..exceptions import MissingConfigError, InvalidConfigError

# Load environment variables
load_dotenv()

# LangChain Configuration
LANGCHAIN_TRACING_V2: Optional[str] = os.getenv('LANGCHAIN_TRACING_V2')
LANGCHAIN_ENDPOINT: Optional[str] = os.getenv('LANGCHAIN_ENDPOINT')
LANGCHAIN_API_KEY: Optional[str] = os.getenv('LANGCHAIN_API_KEY')
LANGCHAIN_PROJECT: Optional[str] = os.getenv('LANGCHAIN_PROJECT')

# API Keys
GOOGLE_API_KEY: Optional[str] = os.getenv('GOOGLE_API_KEY')
OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
TAVILY_API_KEY: Optional[str] = os.getenv('TAVILY_API_KEY')

# Database Configuration
DATABASE_URL: str = os.getenv('DATABASE_URL', 'postgresql://polibase_user:polibase_password@localhost:5432/polibase_db')

# GCS Configuration
GCS_BUCKET_NAME: str = os.getenv('GCS_BUCKET_NAME', 'polibase-scraped-minutes')
GCS_PROJECT_ID: Optional[str] = os.getenv('GCS_PROJECT_ID')  # Optional, uses default if not set
GCS_UPLOAD_ENABLED: bool = os.getenv('GCS_UPLOAD_ENABLED', 'false').lower() == 'true'


def validate_config() -> None:
    """Validate required configuration values"""
    # Check if Google API key is set when needed
    if not GOOGLE_API_KEY:
        import warnings
        warnings.warn(
            "GOOGLE_API_KEY is not set. LLM features will not work. "
            "Please set it in your .env file or environment variables.",
            RuntimeWarning
        )
    
    # Validate DATABASE_URL format
    if not DATABASE_URL.startswith(('postgresql://', 'postgres://')):
        raise InvalidConfigError(
            "DATABASE_URL must be a valid PostgreSQL connection string",
            {"current_value": DATABASE_URL[:30] + "..." if len(DATABASE_URL) > 30 else DATABASE_URL}
        )


def set_env() -> None:
    """Set environment variables from loaded configuration"""
    env_vars = {
        'LANGCHAIN_TRACING_V2': LANGCHAIN_TRACING_V2,
        'LANGCHAIN_ENDPOINT': LANGCHAIN_ENDPOINT,
        'LANGCHAIN_API_KEY': LANGCHAIN_API_KEY,
        'LANGCHAIN_PROJECT': LANGCHAIN_PROJECT,
        'GOOGLE_API_KEY': GOOGLE_API_KEY,
        'OPENAI_API_KEY': OPENAI_API_KEY,
        'TAVILY_API_KEY': TAVILY_API_KEY,
        'DATABASE_URL': DATABASE_URL,
    }
    
    for key, value in env_vars.items():
        if value is not None:
            os.environ[key] = value


def get_required_config(key: str) -> str:
    """Get a required configuration value or raise an error
    
    Args:
        key: The configuration key to retrieve
        
    Returns:
        The configuration value
        
    Raises:
        MissingConfigError: If the configuration is not set
    """
    value = globals().get(key)
    if value is None:
        raise MissingConfigError(
            f"Required configuration '{key}' is not set",
            {"key": key}
        )
    return value
