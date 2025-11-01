"""Backward compatibility stub for prompt_manager.

.. deprecated::
    This module has moved to src.infrastructure.external.prompt_manager.
    Please update your imports.
"""

import warnings

warnings.warn(
    "Importing from 'src.services.prompt_manager' is deprecated. "
    "Use 'src.infrastructure.external.prompt_manager' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from new location
from src.infrastructure.external.prompt_manager import PromptManager  # noqa: E402

__all__ = ["PromptManager"]
