"""Backward compatibility stub for japan_map.

.. deprecated::
    This module has moved to src.infrastructure.utilities.japan_map.
    Please update your imports.
"""

import warnings

warnings.warn(
    "Importing from 'src.utils.japan_map' is deprecated. "
    "Use 'src.infrastructure.utilities.japan_map' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from new location
from src.infrastructure.utilities.japan_map import create_japan_map  # noqa: E402

__all__ = ["create_japan_map"]
