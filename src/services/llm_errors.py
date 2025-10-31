"""Backward compatibility stub for llm_errors.

.. deprecated::
    This module has moved to src.infrastructure.external.llm_errors.
    Please update your imports.
"""

import warnings

warnings.warn(
    "Importing from 'src.services.llm_errors' is deprecated. "
    "Use 'src.infrastructure.external.llm_errors' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from new location
from src.infrastructure.external.llm_errors import (  # noqa: E402
    LLMAuthenticationError,
    LLMError,
    LLMInvalidResponseError,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMTimeoutError,
)

__all__ = [
    "LLMError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMInvalidResponseError",
    "LLMAuthenticationError",
    "LLMQuotaExceededError",
]
