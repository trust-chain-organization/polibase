"""CLI commands for database operations"""

import subprocess

import click

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
    @click.argument("action", type=click.Choice(["backup", "restore", "list"]))
    @click.argument("filename", required=False)
    @click.option("--gcs/--no-gcs", default=True, help="GCSを使用する/しない")
    @with_error_handling
    def database(action: str, filename: str | None, gcs: bool):
        """Database management commands (データベース管理)

        Actions:
        - backup: Create a new backup (local and optionally GCS)
        - restore: Restore from a backup file (local or GCS)
        - list: List available backups (local and GCS)

        Examples:
        - polibase database backup                     # Backup to local and GCS
        - polibase database backup --no-gcs            # Backup to local only
        - polibase database restore backup.sql         # Restore from local file
        - polibase database restore gs://bucket/x.sql  # Restore from GCS
        - polibase database list                       # List all backups
        """
        import sys
        from pathlib import Path

        # Use new GCS-enabled backup script
        script_path = (
            Path(__file__).parent.parent.parent.parent
            / "scripts"
            / "backup-database-gcs.py"
        )

        if action == "backup":
            DatabaseCommands.show_progress("Creating database backup...")
            args = [sys.executable, str(script_path), "backup"]
            if not gcs:
                args.append("--no-gcs")
            result = subprocess.run(args)
            if result.returncode == 0:
                DatabaseCommands.success("Backup completed successfully!")
            else:
                DatabaseCommands.error("Backup failed")

        elif action == "restore":
            if not filename:
                DatabaseCommands.error("Error: filename required for restore")
                return
            DatabaseCommands.show_progress(f"Restoring from backup: {filename}")
            result = subprocess.run(
                [sys.executable, str(script_path), "restore", filename]
            )
            if result.returncode == 0:
                DatabaseCommands.success("Restore completed successfully!")
            else:
                DatabaseCommands.error("Restore failed")

        elif action == "list":
            args = [sys.executable, str(script_path), "list"]
            if not gcs:
                args.append("--no-gcs")
            subprocess.run(args)

    @staticmethod
    @click.command()
    @with_error_handling
    def reset_database():
        """Reset database to initial state (データベースリセット)

        WARNING: This will delete all data and restore to initial state!
        """
        if DatabaseCommands.confirm(
            "Are you sure you want to reset the database? This will delete all data!"
        ):
            subprocess.run(["./reset-database.sh"])
            DatabaseCommands.success("Database reset complete.")
        else:
            DatabaseCommands.show_progress("Database reset cancelled.")

    @staticmethod
    @click.command()
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
    @with_error_handling
    def extract_speakers(
        minutes_id: int | None,
        use_llm: bool,
        skip_extraction: bool,
        skip_politician_link: bool,
        skip_conversation_link: bool,
    ):
        """Extract speakers from minutes and link to politicians.

        議事録から発言者を抽出してspeaker/politicianと紐付けます。
        """
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from src.config.database import DATABASE_URL
        from src.extract_speakers_from_minutes import SpeakerExtractorFromMinutes

        DatabaseCommands.show_progress(
            "議事録から発言者を抽出してspeaker/politicianと紐付けます"
        )

        # データベース接続
        engine = create_engine(DATABASE_URL)
        session_local = sessionmaker(bind=engine)

        with session_local() as session:
            extractor = SpeakerExtractorFromMinutes(session)

            try:
                # 1. 発言者抽出
                if not skip_extraction:
                    DatabaseCommands.show_progress("発言者抽出を開始...")
                    extractor.extract_speakers_from_minutes(minutes_id)
                    DatabaseCommands.success("発言者抽出が完了しました")

                # 2. speaker-politician紐付け
                if not skip_politician_link:
                    DatabaseCommands.show_progress("speaker-politician紐付けを開始...")
                    extractor.link_speakers_to_politicians(use_llm=use_llm)
                    DatabaseCommands.success("speaker-politician紐付けが完了しました")

                # 3. conversation-speaker紐付け
                if not skip_conversation_link:
                    DatabaseCommands.show_progress(
                        "conversation-speaker紐付けを開始..."
                    )
                    extractor.update_conversation_speaker_links(use_llm=use_llm)
                    DatabaseCommands.success("conversation-speaker紐付けが完了しました")

                DatabaseCommands.success("全処理が完了しました！")

            except Exception as e:
                DatabaseCommands.error(f"エラー: {e}")
                session.rollback()
                raise


def get_database_commands():
    """Get all database-related commands"""
    return [
        DatabaseCommands.test_connection,
        DatabaseCommands.database,
        DatabaseCommands.reset_database,
        DatabaseCommands.extract_speakers,
    ]
