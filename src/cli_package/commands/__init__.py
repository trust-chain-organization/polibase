"""CLI commands package"""

from .conference_member_commands import get_conference_member_commands
from .coverage_commands import get_coverage_commands
from .database_commands import get_database_commands
from .minutes_commands import get_minutes_commands
from .parliamentary_group_commands import get_parliamentary_group_commands
from .politician_commands import get_politician_commands
from .scraping_commands import get_scraping_commands
from .seed_commands import get_seed_commands
from .ui_commands import get_ui_commands

__all__ = [
    "get_minutes_commands",
    "get_scraping_commands",
    "get_politician_commands",
    "get_ui_commands",
    "get_database_commands",
    "get_conference_member_commands",
    "get_parliamentary_group_commands",
    "get_seed_commands",
    "get_coverage_commands",
]
