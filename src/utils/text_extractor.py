"""Backward compatibility stub for text_extractor.

.. deprecated::
    This module has moved to src.infrastructure.utilities.text_extractor.
    Please update your imports.
"""

import warnings

warnings.warn(
    "Importing from 'src.utils.text_extractor' is deprecated. "
    "Use 'src.infrastructure.utilities.text_extractor' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from new location
from src.infrastructure.utilities.text_extractor import (  # noqa: E402
    extract_text_from_file,
    extract_text_from_pdf,
)

__all__ = ["extract_text_from_pdf", "extract_text_from_file"]
