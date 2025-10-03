"""Database management CLI commands."""

import click

from src.interfaces.cli.base import with_error_handling
from src.interfaces.cli.commands.database.backup import BackupCommand
from src.interfaces.cli.commands.database.connection import TestConnectionCommand
from src.interfaces.cli.commands.database.reset import ResetDatabaseCommand
from src.interfaces.cli.commands.database.restore import RestoreCommand


@click.group()
def database():
    """Database management commands (データベース管理)."""
    pass


@database.command()
@with_error_handling
def test_connection():
    """Test database connection (データベース接続テスト)."""
    command = TestConnectionCommand()
    command.execute()


@database.command()
@click.option("--gcs/--no-gcs", default=True, help="GCSを使用する/しない")
@with_error_handling
def backup(gcs: bool):
    """Create database backup (データベースバックアップ)."""
    command = BackupCommand()
    command.execute(gcs=gcs)


@database.command()
@click.argument("filename")
@with_error_handling
def restore(filename: str):
    """Restore database from backup (データベースリストア)."""
    command = RestoreCommand()
    command.execute(filename=filename)


@database.command()
@click.option("--gcs/--no-gcs", default=True, help="GCSを使用する/しない")
@with_error_handling
def list_backups(gcs: bool):
    """List available backups (バックアップ一覧)."""
    from src.interfaces.cli.commands.database.list_backups import ListBackupsCommand

    command = ListBackupsCommand()
    command.execute(gcs=gcs)


@database.command()
@with_error_handling
def reset():
    """Reset database to initial state (データベースリセット)."""
    command = ResetDatabaseCommand()
    command.execute()
