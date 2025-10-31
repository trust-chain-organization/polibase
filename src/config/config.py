"""
DEPRECATED: This module has moved to src.infrastructure.config.config

Please update imports to:
    from src.infrastructure.config import config
    # or
    import src.infrastructure.config.config as config
"""

import warnings

# Re-export everything from the new location
from src.infrastructure.config.config import *  # noqa: F401, F403

warnings.warn(
    "src.config.config is deprecated. Use src.infrastructure.config.config instead.",
    DeprecationWarning,
    stacklevel=2,
)
