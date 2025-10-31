"""
DEPRECATED: This module has moved to src.infrastructure.config.async_database

Please update imports to:
    from src.infrastructure.config import async_database
    # or
    import src.infrastructure.config.async_database as async_database
"""

import warnings

# Re-export everything from the new location
from src.infrastructure.config.async_database import *  # noqa: F401, F403

warnings.warn(
    "src.config.async_database is deprecated. "
    "Use src.infrastructure.config.async_database instead.",
    DeprecationWarning,
    stacklevel=2,
)
