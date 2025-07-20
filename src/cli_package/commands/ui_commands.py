"""CLI commands for user interface operations"""

import subprocess
import sys

import click

from ..base import BaseCommand, with_error_handling


class UICommands(BaseCommand):
    """Commands for launching user interfaces"""

    @staticmethod
    @click.command()
    @click.option("--port", default=8501, help="Port number for Streamlit app")
    @click.option("--host", default="0.0.0.0", help="Host address")
    @with_error_handling
    def streamlit(port: int, host: str):
        """Launch Streamlit web interface with URL-based routing

        URLベースルーティング対応Web UI

        This command starts a web interface with URL-based navigation where you can:
        - Access different pages directly via URLs (e.g., /meetings, /parties)
        - View and manage meetings (会議管理)
        - Manage political parties and member lists (政党管理)
        - Manage conferences (会議体管理)
        - Manage conference members (会議体メンバー管理)
        - And more features with modern navigation
        """
        # Docker環境での実行を考慮
        if host == "0.0.0.0":
            access_url = f"http://localhost:{port}"
        else:
            access_url = f"http://{host}:{port}"

        UICommands.show_progress("Starting Streamlit app with URL routing...")
        UICommands.show_progress(f"Access the app at: {access_url}")
        UICommands.show_progress("Available URLs:")
        UICommands.show_progress(f"  - {access_url}/             (Home)")
        UICommands.show_progress(f"  - {access_url}/meetings     (会議管理)")
        UICommands.show_progress(f"  - {access_url}/parties      (政党管理)")
        UICommands.show_progress(f"  - {access_url}/conferences  (会議体管理)")
        UICommands.show_progress("  ... and more")
        UICommands.show_progress("Press Ctrl+C to stop the server")

        # 新しいStreamlitアプリケーションを起動
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "src/streamlit/app.py",
                "--server.port",
                str(port),
                "--server.address",
                host,
                "--server.headless",
                "true",  # Dockerでの実行に必要
            ]
        )

    @staticmethod
    @click.command()
    @click.option("--port", default=8502, help="Port number for monitoring dashboard")
    @click.option("--host", default="0.0.0.0", help="Host address")
    @with_error_handling
    def monitoring(port: int, host: str):
        """Launch monitoring dashboard for data coverage visualization.

        データカバレッジ監視ダッシュボード

        This command starts a monitoring dashboard where you can:
        - View overall data coverage metrics
        - Monitor conference-wise data completion
        - Analyze timeline of data input activities
        - Track detailed coverage by party, prefecture, and committee type
        """
        # Docker環境での実行を考慮
        if host == "0.0.0.0":
            access_url = f"http://localhost:{port}"
        else:
            access_url = f"http://{host}:{port}"

        UICommands.show_progress("Starting monitoring dashboard...")
        UICommands.show_progress(f"Access the dashboard at: {access_url}")
        UICommands.show_progress("Press Ctrl+C to stop the server")

        # 監視ダッシュボードを起動
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "src/monitoring_app.py",
                "--server.port",
                str(port),
                "--server.address",
                host,
                "--server.headless",
                "true",  # Dockerでの実行に必要
            ]
        )


def get_ui_commands():
    """Get all UI-related commands"""
    return [UICommands.streamlit, UICommands.monitoring]
