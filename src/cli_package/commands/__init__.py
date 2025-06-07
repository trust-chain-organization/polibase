"""CLI commands package"""
from .minutes_commands import get_minutes_commands
from .scraping_commands import get_scraping_commands
from .politician_commands import get_politician_commands
from .ui_commands import get_ui_commands
from .database_commands import get_database_commands

__all__ = [
    'get_minutes_commands',
    'get_scraping_commands',
    'get_politician_commands',
    'get_ui_commands',
    'get_database_commands'
]