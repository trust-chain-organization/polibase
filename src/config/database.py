"""
DEPRECATED: This module has moved to src.infrastructure.config.database

Please update imports to:
    from src.infrastructure.config import database
    # or
    import src.infrastructure.config.database as database
"""

import warnings

# Re-export everything from the new location
from src.infrastructure.config.database import *  # noqa: F401, F403

warnings.warn(
    "src.config.database is deprecated. "
    "Use src.infrastructure.config.database instead.",
    DeprecationWarning,
    stacklevel=2,
)
