"""Database connection test command."""

from typing import Any

from src.interfaces.cli.base import BaseCommand, Command


class TestConnectionCommand(Command, BaseCommand):
    """Command to test database connection."""

    def execute(self, **kwargs: Any) -> None:
        """Test database connection."""
        from src.infrastructure.config.database import test_connection as test_db

        self.show_progress("Testing database connection...")
        test_db()
        self.success("Database connection successful!")
