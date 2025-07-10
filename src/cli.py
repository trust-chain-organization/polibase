"""Unified CLI for Polibase - Political Meeting Minutes Processing System

Provides a comprehensive command-line interface for all Polibase operations.
"""

import logging
import os
import sys

import click

# Add parent directory to path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import logging and configuration modules
# Import command modules
from src.cli_package.commands import (
    get_conference_member_commands,
    get_coverage_commands,
    get_database_commands,
    get_minutes_commands,
    get_parliamentary_group_commands,
    get_politician_commands,
    get_scraping_commands,
    get_seed_commands,
    get_ui_commands,
)
from src.common.logging import setup_logging
from src.config.sentry import init_sentry
from src.config.settings import get_settings

# Initialize settings
settings = get_settings()

# Initialize structured logging with Sentry integration
setup_logging(
    log_level=settings.log_level, json_format=settings.is_production, enable_sentry=True
)

# Initialize Sentry SDK
init_sentry()

# Get logger after setup
logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """Polibase - 政治活動追跡アプリケーション

    A unified command-line interface for processing political meeting minutes,
    extracting politician information, and managing speaker data.
    """
    pass


def register_commands(cli_group: click.Group) -> None:
    """Register all commands to the CLI group

    Args:
        cli_group: Click group to register commands to
    """
    command_getters = [
        get_minutes_commands,
        get_scraping_commands,
        get_politician_commands,
        get_ui_commands,
        get_database_commands,
        get_conference_member_commands,
        get_parliamentary_group_commands,
        get_seed_commands,
        get_coverage_commands,
    ]

    for getter in command_getters:
        try:
            commands = getter()
            for command in commands:
                cli_group.add_command(command)
        except Exception as e:
            logger.error(f"Failed to register commands from {getter.__name__}: {e}")
            # Continue with other command groups


# Register all commands
register_commands(cli)


if __name__ == "__main__":
    try:
        cli()
    except Exception as e:
        # Log the error
        logger.error(f"Unhandled exception in CLI: {e}", exc_info=True)
        # Re-raise to show the error to the user
        raise
