"""Processing-related CLI commands."""

import click

from src.interfaces.cli.commands.minutes_commands import MinutesCommands


@click.group()
def processing():
    """Processing commands (処理コマンド)."""
    pass


# Re-export existing processing commands temporarily
# These will be refactored to use Clean Architecture patterns in a future iteration
processing.add_command(MinutesCommands.process_minutes, "process-minutes")
processing.add_command(MinutesCommands.update_speakers, "update-speakers")
