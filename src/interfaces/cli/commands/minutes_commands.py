"""CLI commands for processing meeting minutes"""

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
    def process_minutes(pdf: str, output: str):
        """Process meeting minutes to extract conversations (議事録分割処理)

        This command reads a PDF file containing meeting minutes and extracts
        individual speeches/conversations using LLM processing.

        Note: This command has been deprecated. Please use the DI
        container-based process-minutes command with specific options like
        --meeting-id or --process-all-gcs.
        """
        MinutesCommands.error(
            "This command is deprecated. Please use 'sagebase process-minutes --help' "
            "for the updated command options.",
            exit_code=1,
        )

    @staticmethod
    @click.command()
    @click.option("--use-llm", is_flag=True, help="Use LLM for fuzzy matching")
    @click.option(
        "--interactive/--no-interactive",
        default=True,
        help="Enable interactive confirmation",
    )
    @click.option(
        "--limit",
        type=int,
        default=None,
        help="Limit number of speakers to process",
    )
    @with_error_handling
    def update_speakers(use_llm: bool, interactive: bool, limit: int | None):
        """Update speaker links in database (発言者紐付け更新)

        This command links conversations to speaker records. Use --use-llm
        for advanced fuzzy matching with Google Gemini API.

        Now uses Clean Architecture MatchSpeakersUseCase for improved
        maintainability and testability.
        """
        from src.infrastructure.di.container import get_container, init_container

        MinutesCommands.show_progress(
            f"Using {'LLM-based' if use_llm else 'rule-based'} speaker matching..."
        )

        # Initialize and get dependencies from DI container
        try:
            container = get_container()
        except RuntimeError:
            # Container not initialized yet
            container = init_container()

        match_speakers_usecase = container.use_cases.match_speakers_usecase()

        # Execute matching
        results = match_speakers_usecase.execute(use_llm=use_llm, limit=limit)

        # Report results
        matched = sum(1 for r in results if r.matched_politician_id is not None)
        total = len(results)
        success_rate = (matched / total * 100) if total > 0 else 0

        MinutesCommands.show_progress(
            f"Processed {total} speakers, matched {matched} ({success_rate:.1f}%)"
        )
        MinutesCommands.success("Speaker links updated successfully")


def get_minutes_commands():
    """Get all minutes-related commands"""
    from src.interfaces.cli.commands.analyze_matching_history import (
        get_analyze_matching_history_command,
    )

    return [
        MinutesCommands.process_minutes,
        MinutesCommands.update_speakers,
        get_analyze_matching_history_command(),
    ]
