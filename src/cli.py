"""
DEPRECATED: This file is deprecated and will be removed in a future version.

Please use the new unified CLI interface instead:
    from src.interfaces.cli.cli import main

Or use the command:
    uv run polibase --help

See: https://github.com/trust-chain-organization/polibase/tree/main/src/interfaces/cli

This file now delegates to the Clean Architecture implementation in src/interfaces/cli/
"""

import os
import sys
import warnings

# Show deprecation warning when this module is imported or executed
warnings.warn(
    "src.cli is deprecated. Use 'uv run polibase' command or "
    "'from src.interfaces.cli.cli import main' instead. "
    "See: src/interfaces/cli/",
    DeprecationWarning,
    stacklevel=2,
)

# Add parent directory to path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import and re-export the new CLI implementation
from src.interfaces.cli.cli import cli, main  # noqa: E402

# Export these for backward compatibility
__all__ = ["cli", "main"]

if __name__ == "__main__":
    main()
