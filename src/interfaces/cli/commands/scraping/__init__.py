"""Web scraping CLI commands."""

import click

from src.interfaces.cli.commands.scraping_commands import ScrapingCommands


@click.group()
def scraping():
    """Web scraping commands (Webスクレイピング)."""
    pass


# Re-export existing scraping commands temporarily
# These will be refactored to use Clean Architecture patterns in a future iteration
scraping.add_command(ScrapingCommands.scrape_minutes, "scrape-minutes")
scraping.add_command(ScrapingCommands.batch_scrape, "batch-scrape")
