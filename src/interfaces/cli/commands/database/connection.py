"""Database connection test command."""

from typing import Any

from src.interfaces.cli.base import BaseCommand, Command, with_error_handling


class TestConnectionCommand(Command, BaseCommand):
    """Command to test database connection."""

    @with_error_handling
    def execute(self, **kwargs: Any) -> None:
        """Test database connection."""
        from src.config.database import test_connection as test_db

        self.show_progress("Testing database connection...")
        test_db()
        self.success("Database connection successful!")
