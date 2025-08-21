"""Database management CLI commands."""

import click

from src.interfaces.cli.commands.database.backup import BackupCommand
from src.interfaces.cli.commands.database.connection import TestConnectionCommand
from src.interfaces.cli.commands.database.reset import ResetDatabaseCommand
from src.interfaces.cli.commands.database.restore import RestoreCommand
from src.interfaces.cli.commands.database.speakers import ExtractSpeakersCommand


@click.group()
def database():
    """Database management commands (データベース管理)."""
    pass


@database.command()
def test_connection():
    """Test database connection (データベース接続テスト)."""
    command = TestConnectionCommand()
    command.execute()


@database.command()
@click.option("--gcs/--no-gcs", default=True, help="GCSを使用する/しない")
def backup(gcs: bool):
    """Create database backup (データベースバックアップ)."""
    command = BackupCommand()
    command.execute(gcs=gcs)


@database.command()
@click.argument("filename")
def restore(filename: str):
    """Restore database from backup (データベースリストア)."""
    command = RestoreCommand()
    command.execute(filename=filename)


@database.command()
@click.option("--gcs/--no-gcs", default=True, help="GCSを使用する/しない")
def list_backups(gcs: bool):
    """List available backups (バックアップ一覧)."""
    from src.interfaces.cli.commands.database.list_backups import ListBackupsCommand

    command = ListBackupsCommand()
    command.execute(gcs=gcs)


@database.command()
def reset():
    """Reset database to initial state (データベースリセット)."""
    command = ResetDatabaseCommand()
    command.execute()


@database.command()
@click.option("--minutes-id", type=int, help="特定の議事録IDのみを処理")
@click.option("--use-llm", is_flag=True, help="LLMを使用した高度なマッチングを行う")
@click.option(
    "--skip-extraction",
    is_flag=True,
    help="発言者抽出をスキップ（紐付けのみ実行）",
)
@click.option(
    "--skip-politician-link",
    is_flag=True,
    help="politician紐付けをスキップ",
)
@click.option(
    "--skip-conversation-link",
    is_flag=True,
    help="conversation紐付けをスキップ",
)
def extract_speakers(
    minutes_id: int | None,
    use_llm: bool,
    skip_extraction: bool,
    skip_politician_link: bool,
    skip_conversation_link: bool,
):
    """Extract speakers from minutes and link to politicians."""
    command = ExtractSpeakersCommand()
    command.execute(
        minutes_id=minutes_id,
        use_llm=use_llm,
        skip_extraction=skip_extraction,
        skip_politician_link=skip_politician_link,
        skip_conversation_link=skip_conversation_link,
    )
