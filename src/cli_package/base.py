"""Base classes and utilities for CLI commands"""

import asyncio
import sys
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

import click

from src.application.exceptions import ConfigurationError, ProcessingError
from src.domain.exceptions import PolibaseError
from src.infrastructure.exceptions import (
    APIKeyError,
    ConnectionError,
    DatabaseError,
    LLMError,
    RecordNotFoundError,
    ScrapingError,
    StorageError,
)

ValidationError = ProcessingError  # Alias for backward compatibility

P = ParamSpec("P")
T = TypeVar("T")


class BaseCommand:
    """Base class for CLI commands with common functionality"""

    @staticmethod
    def async_command(f: Callable[P, T]) -> Callable[P, T]:
        """Decorator to run async functions in CLI commands"""

        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return asyncio.run(f(*args, **kwargs))  # type: ignore

        return wrapper

    @staticmethod
    def handle_errors(f: Callable[P, T]) -> Callable[P, T]:
        """Decorator to handle common errors in CLI commands"""

        @wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return f(*args, **kwargs)
            except APIKeyError as e:
                click.echo(f"API Key Error: {str(e)}", err=True)
                click.echo(
                    "Please set the required API key in your environment variables.",
                    err=True,
                )
                sys.exit(2)
            except ConfigurationError as e:
                click.echo(f"Configuration Error: {str(e)}", err=True)
                click.echo("Please check your configuration settings.", err=True)
                sys.exit(2)
            except ConnectionError as e:
                click.echo(f"Connection Error: {str(e)}", err=True)
                click.echo(
                    "Please check your network connection and database settings.",
                    err=True,
                )
                sys.exit(3)
            except RecordNotFoundError as e:
                click.echo(f"Not Found: {str(e)}", err=True)
                sys.exit(4)
            except ValidationError as e:
                click.echo(f"Validation Error: {str(e)}", err=True)
                sys.exit(5)
            except PolibaseError as e:
                click.echo(f"Error: {str(e)}", err=True)
                sys.exit(1)
            except KeyboardInterrupt:
                click.echo("\nOperation cancelled by user", err=True)
                sys.exit(0)
            except Exception as e:
                click.echo(f"Unexpected Error: {str(e)}", err=True)
                click.echo(
                    "This is an unexpected error. Please report it.",
                    err=True,
                )
                sys.exit(99)

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


def with_async_execution(func: Callable[P, T]) -> Callable[P, T]:  # noqa: UP047
    """Decorator to execute async functions in sync context"""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return asyncio.run(func(*args, **kwargs))  # type: ignore

    return wrapper


def with_error_handling(func: Callable[P, T]) -> Callable[P, T]:  # noqa: UP047
    """Decorator to handle errors gracefully with specific error types"""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except APIKeyError as e:
            click.echo(f"\nAPI Key Error: {str(e)}", err=True)
            click.echo(
                "Please set the required API key in your environment variables.",
                err=True,
            )
            sys.exit(2)
        except ConfigurationError as e:
            click.echo(f"\nConfiguration Error: {str(e)}", err=True)
            click.echo("Please check your configuration settings.", err=True)
            sys.exit(2)
        except ConnectionError as e:
            click.echo(f"\nConnection Error: {str(e)}", err=True)
            click.echo(
                "Please check your network connection and database settings.", err=True
            )
            sys.exit(3)
        except RecordNotFoundError as e:
            click.echo(f"\nNot Found: {str(e)}", err=True)
            sys.exit(4)
        except ValidationError as e:
            click.echo(f"\nValidation Error: {str(e)}", err=True)
            if e.details:
                click.echo(f"Details: {e.details}", err=True)
            sys.exit(5)
        except DatabaseError as e:
            click.echo(f"\nDatabase Error: {str(e)}", err=True)
            if e.details:
                click.echo(f"Details: {e.details}", err=True)
            sys.exit(10)
        except ScrapingError as e:
            click.echo(f"\nScraping Error: {str(e)}", err=True)
            if e.details:
                click.echo(f"Details: {e.details}", err=True)
            sys.exit(11)
        except LLMError as e:
            click.echo(f"\nLLM Error: {str(e)}", err=True)
            if e.details:
                click.echo(f"Details: {e.details}", err=True)
            sys.exit(13)
        except StorageError as e:
            click.echo(f"\nStorage Error: {str(e)}", err=True)
            if e.details:
                click.echo(f"Details: {e.details}", err=True)
            sys.exit(14)
        except PolibaseError as e:
            # Catch any other custom exceptions
            click.echo(f"\nError: {str(e)}", err=True)
            if e.details:
                click.echo(f"Details: {e.details}", err=True)
            sys.exit(1)
        except KeyboardInterrupt:
            click.echo("\nOperation cancelled by user", err=True)
            sys.exit(0)
        except Exception as e:
            click.echo(f"\nUnexpected Error: {str(e)}", err=True)
            click.echo(
                "This is an unexpected error. Please report it.",
                err=True,
            )
            sys.exit(99)

    return wrapper


def format_output_path(base_path: str, filename: str) -> str:
    """Format output path with proper separators"""
    import os

    return os.path.join(base_path, filename)
