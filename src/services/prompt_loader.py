"""Backward compatibility stub for prompt_loader.

.. deprecated::
    This module has moved to src.infrastructure.external.prompt_loader.
    Please update your imports.
"""

import warnings

warnings.warn(
    "Importing from 'src.services.prompt_loader' is deprecated. "
    "Use 'src.infrastructure.external.prompt_loader' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from new location
from src.infrastructure.external.prompt_loader import PromptLoader  # noqa: E402

__all__ = ["PromptLoader"]
