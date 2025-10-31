"""
DEPRECATED: This module has moved to src.infrastructure.config.sentry

Please update imports to:
    from src.infrastructure.config import sentry
    # or
    import src.infrastructure.config.sentry as sentry
"""

import warnings

# Re-export everything from the new location
from src.infrastructure.config.sentry import *  # noqa: F401, F403

warnings.warn(
    "src.config.sentry is deprecated. Use src.infrastructure.config.sentry instead.",
    DeprecationWarning,
    stacklevel=2,
)
