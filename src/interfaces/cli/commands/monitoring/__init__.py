"""Monitoring and UI CLI commands."""

import click

from src.cli_package.commands.ui_commands import UICommands


@click.group()
def monitoring():
    """Monitoring and UI commands (モニタリング・UI)."""
    pass


# Re-export existing UI commands temporarily
# These will be refactored to use Clean Architecture patterns in a future iteration
monitoring.add_command(UICommands.streamlit, "streamlit")
monitoring.add_command(UICommands.monitoring, "dashboard")
