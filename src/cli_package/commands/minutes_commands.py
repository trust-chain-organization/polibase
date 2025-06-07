"""CLI commands for processing meeting minutes"""

import sys

import click

from ..base import BaseCommand, with_error_handling


class MinutesCommands(BaseCommand):
    """Commands for processing meeting minutes"""

    @staticmethod
    @click.command()
    @click.option(
        "--pdf",
        default="data/minutes.pdf",
        help="Path to the PDF file containing meeting minutes",
    )
    @click.option(
        "--output",
        default="data/output/meeting_output.csv",
        help="Output CSV file path",
    )
    @with_error_handling
    def process_minutes(pdf, output):
        """Process meeting minutes to extract conversations (議事録分割処理)

        This command reads a PDF file containing meeting minutes and extracts
        individual speeches/conversations using LLM processing.
        """
        from src.process_minutes import main

        MinutesCommands.show_progress(f"Processing minutes from: {pdf}")
        MinutesCommands.show_progress(f"Output will be saved to: {output}")
        main()
        MinutesCommands.success("Minutes processing completed")

    @staticmethod
    @click.command()
    @click.option("--use-llm", is_flag=True, help="Use LLM for fuzzy matching")
    @click.option(
        "--interactive/--no-interactive",
        default=True,
        help="Enable interactive confirmation",
    )
    @with_error_handling
    def update_speakers(use_llm, interactive):
        """Update speaker links in database (発言者紐付け更新)

        This command links conversations to speaker records. Use --use-llm
        for advanced fuzzy matching with Google Gemini API.
        """
        if use_llm:
            MinutesCommands.show_progress("Using LLM-based speaker matching...")
            # Import inside to avoid circular imports
            sys.path.insert(0, ".")
            from update_speaker_links_llm import main

            main()
        else:
            MinutesCommands.show_progress("Using rule-based speaker matching...")
            sys.path.insert(0, ".")
            from update_speaker_links import main

            main()

        MinutesCommands.success("Speaker links updated successfully")


def get_minutes_commands():
    """Get all minutes-related commands"""
    return [MinutesCommands.process_minutes, MinutesCommands.update_speakers]
