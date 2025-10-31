"""
DEPRECATED: This module has moved to src.infrastructure.config.settings

Please update imports to:
    from src.infrastructure.config import settings
    # or
    import src.infrastructure.config.settings as settings
"""

import warnings

# Re-export everything from the new location
from src.infrastructure.config.settings import *  # noqa: F401, F403

warnings.warn(
    "src.config.settings is deprecated. "
    "Use src.infrastructure.config.settings instead.",
    DeprecationWarning,
    stacklevel=2,
)
