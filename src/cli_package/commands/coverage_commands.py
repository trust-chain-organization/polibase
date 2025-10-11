"""Coverage reporting commands for Polibase"""

import click
from sqlalchemy import text

from src.infrastructure.di.container import get_container, init_container


def get_coverage_commands() -> list[click.Command]:
    """Get all coverage-related commands

    Returns:
        List of Click commands
    """
    return [coverage]


@click.command()
def coverage():
    """Show data coverage statistics for governing bodies."""
    # Initialize and get dependencies from DI container
    try:
        container = get_container()
    except RuntimeError:
        container = init_container()

    engine = container.database.engine()

    with engine.connect() as conn:
        # Total governing bodies
        result = conn.execute(text("SELECT COUNT(*) FROM governing_bodies"))
        total_governing_bodies = result.scalar()

        # Total governing bodies by type
        type_stats = conn.execute(
            text("""
            SELECT type, organization_type, COUNT(*) as count
            FROM governing_bodies
            GROUP BY type, organization_type
            ORDER BY type, organization_type
        """)
        ).fetchall()

        # Governing bodies with conferences
        result = conn.execute(
            text("""
            SELECT COUNT(DISTINCT governing_body_id)
            FROM conferences
        """)
        )
        bodies_with_conferences = result.scalar()

        # Governing bodies with meetings
        result = conn.execute(
            text("""
            SELECT COUNT(DISTINCT c.governing_body_id)
            FROM meetings m
            JOIN conferences c ON m.conference_id = c.id
        """)
        )
        bodies_with_meetings = result.scalar()

        # Coverage percentage
        if bodies_with_conferences is not None and total_governing_bodies is not None:
            conference_coverage = (
                (bodies_with_conferences / total_governing_bodies * 100)
                if total_governing_bodies > 0
                else 0
            )
        else:
            conference_coverage = 0

        if bodies_with_meetings is not None and total_governing_bodies is not None:
            meeting_coverage = (
                (bodies_with_meetings / total_governing_bodies * 100)
                if total_governing_bodies > 0
                else 0
            )
        else:
            meeting_coverage = 0

        # Display results
        click.echo("=== Governing Bodies Coverage Report ===\n")

        click.echo(f"Total governing bodies: {total_governing_bodies:,}")
        click.echo(
            f"Bodies with conferences: {bodies_with_conferences:,} "
            f"({conference_coverage:.1f}%)"
        )
        click.echo(
            f"Bodies with meetings: {bodies_with_meetings:,} "
            f"({meeting_coverage:.1f}%)\n"
        )

        click.echo("Breakdown by type:")
        click.echo("-" * 50)
        click.echo(f"{'Type':<15} {'Detail':<15} {'Count':>10}")
        click.echo("-" * 50)

        for stat in type_stats:
            org_type = stat.organization_type or "N/A"
            click.echo(f"{stat.type:<15} {org_type:<15} {stat.count:>10,}")

        # Show some uncovered bodies as examples
        uncovered_bodies = conn.execute(
            text("""
            SELECT gb.name, gb.organization_code, gb.organization_type
            FROM governing_bodies gb
            LEFT JOIN conferences c ON gb.id = c.governing_body_id
            WHERE c.id IS NULL
            LIMIT 10
        """)
        ).fetchall()

        if uncovered_bodies:
            click.echo("\nExample governing bodies without conferences:")
            click.echo("-" * 50)
            for body in uncovered_bodies:
                click.echo(
                    f"- {body.name} ({body.organization_type}, "
                    f"code: {body.organization_code})"
                )
