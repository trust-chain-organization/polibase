"""Base classes and utilities for CLI commands"""

import asyncio
import sys
from collections.abc import Callable
from functools import wraps

import click


class BaseCommand:
    """Base class for CLI commands with common functionality"""

    @staticmethod
    def async_command(f):
        """Decorator to run async functions in CLI commands"""

        @wraps(f)
        def wrapper(*args, **kwargs):
            return asyncio.run(f(*args, **kwargs))

        return wrapper

    @staticmethod
    def handle_errors(f):
        """Decorator to handle common errors in CLI commands"""

        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                click.echo(f"Error: {str(e)}", err=True)
                sys.exit(1)

        return wrapper

    @staticmethod
    def show_progress(message: str):
        """Show a progress message"""
        click.echo(message)

    @staticmethod
    def success(message: str):
        """Show a success message"""
        click.echo(f"✓ {message}")

    @staticmethod
    def error(message: str, exit_code: int = 1):
        """Show an error message and optionally exit"""
        click.echo(f"✗ {message}", err=True)
        if exit_code:
            sys.exit(exit_code)

    @staticmethod
    def confirm(message: str) -> bool:
        """Ask for user confirmation"""
        return click.confirm(message)


def with_async_execution(func: Callable) -> Callable:
    """Decorator to execute async functions in sync context"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


def with_error_handling(func: Callable) -> Callable:
    """Decorator to handle errors gracefully"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            click.echo("\nOperation cancelled by user", err=True)
            sys.exit(0)
        except Exception as e:
            click.echo(f"\nError: {str(e)}", err=True)
            sys.exit(1)

    return wrapper


def format_output_path(base_path: str, filename: str) -> str:
    """Format output path with proper separators"""
    import os

    return os.path.join(base_path, filename)
