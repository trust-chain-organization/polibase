"""Unified CLI for Polibase - Political Meeting Minutes Processing System

This file now delegates to the Clean Architecture implementation in src/interfaces/cli/
"""

import os
import sys

# Add parent directory to path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import and re-export the new CLI implementation
from src.interfaces.cli.cli import cli, main

# Export these for backward compatibility
__all__ = ["cli", "main"]

if __name__ == "__main__":
    main()
