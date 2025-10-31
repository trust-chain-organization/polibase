"""Backward compatibility stub for versioned_prompt_manager.

.. deprecated::
    This module has moved to src.infrastructure.external.versioned_prompt_manager.
    Please update your imports.
"""

import warnings

warnings.warn(
    "Importing from 'src.services.versioned_prompt_manager' is deprecated. "
    "Use 'src.infrastructure.external.versioned_prompt_manager' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from new location
from src.infrastructure.external.versioned_prompt_manager import (  # noqa: E402
    VersionedPromptManager,
)

__all__ = ["VersionedPromptManager"]
