"""
Legacy configuration module - DEPRECATED.

This module is deprecated. Please use src.infrastructure.config instead.

This file provides backward compatibility by re-exporting from the new location.
All new code should import directly from src.infrastructure.config.
"""

import warnings

# Re-export from new location for backward compatibility
from src.infrastructure.config import (  # noqa: F401
    DATABASE_URL,
    ENV_FILE_PATH,
    GCS_BUCKET_NAME,
    GCS_PROJECT_ID,
    GCS_UPLOAD_ENABLED,
    GOOGLE_API_KEY,
    LANGCHAIN_API_KEY,
    LANGCHAIN_ENDPOINT,
    LANGCHAIN_PROJECT,
    LANGCHAIN_TRACING_V2,
    OPENAI_API_KEY,
    TAVILY_API_KEY,
    AsyncDatabase,
    Settings,
    async_db,
    close_db_engine,
    find_env_file,
    get_async_session,
    get_db_engine,
    get_db_session,
    get_db_session_context,
    get_required_config,
    init_sentry,
    set_env,
    settings,
    test_connection,
    validate_config,
)

warnings.warn(
    "src.config is deprecated. Use src.infrastructure.config instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "Settings",
    "settings",
    "AsyncDatabase",
    "async_db",
    "get_async_session",
    "DATABASE_URL",
    "ENV_FILE_PATH",
    "GCS_BUCKET_NAME",
    "GCS_PROJECT_ID",
    "GCS_UPLOAD_ENABLED",
    "GOOGLE_API_KEY",
    "LANGCHAIN_API_KEY",
    "LANGCHAIN_ENDPOINT",
    "LANGCHAIN_PROJECT",
    "LANGCHAIN_TRACING_V2",
    "OPENAI_API_KEY",
    "TAVILY_API_KEY",
    "find_env_file",
    "get_required_config",
    "set_env",
    "validate_config",
    "close_db_engine",
    "get_db_engine",
    "get_db_session",
    "get_db_session_context",
    "test_connection",
    "init_sentry",
]
