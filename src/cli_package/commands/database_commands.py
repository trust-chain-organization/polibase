"""CLI commands for database operations"""
import click
import subprocess
import sys
from ..base import BaseCommand, with_error_handling


class DatabaseCommands(BaseCommand):
    """Commands for database management"""
    
    @staticmethod
    @click.command()
    @with_error_handling
    def test_connection():
        """Test database connection (データベース接続テスト)"""
        from src.config.database import test_connection as test_db
        DatabaseCommands.show_progress("Testing database connection...")
        test_db()
        DatabaseCommands.success("Database connection successful!")
    
    @staticmethod
    @click.command()
    @click.argument('action', type=click.Choice(['backup', 'restore', 'list']))
    @click.argument('filename', required=False)
    @with_error_handling
    def database(action, filename):
        """Database management commands (データベース管理)
        
        Actions:
        - backup: Create a new backup
        - restore: Restore from a backup file
        - list: List available backups
        """
        if action == 'backup':
            DatabaseCommands.show_progress("Creating database backup...")
            subprocess.run(['./backup-database.sh', 'backup'])
        elif action == 'restore':
            if not filename:
                DatabaseCommands.error("Error: filename required for restore")
            DatabaseCommands.show_progress(f"Restoring from backup: {filename}")
            subprocess.run(['./backup-database.sh', 'restore', filename])
        elif action == 'list':
            subprocess.run(['./backup-database.sh', 'list'])
    
    @staticmethod
    @click.command()
    @with_error_handling
    def reset_database():
        """Reset database to initial state (データベースリセット)
        
        WARNING: This will delete all data and restore to initial state!
        """
        if DatabaseCommands.confirm('Are you sure you want to reset the database? This will delete all data!'):
            subprocess.run(['./reset-database.sh'])
            DatabaseCommands.success("Database reset complete.")
        else:
            DatabaseCommands.show_progress("Database reset cancelled.")


def get_database_commands():
    """Get all database-related commands"""
    return [
        DatabaseCommands.test_connection,
        DatabaseCommands.database,
        DatabaseCommands.reset_database
    ]