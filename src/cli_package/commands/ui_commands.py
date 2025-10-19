"""CLI commands for user interface operations"""

import os
import subprocess
import sys

import click

from ..base import BaseCommand, with_error_handling


class UICommands(BaseCommand):
    """Commands for launching user interfaces"""

    @staticmethod
    def detect_actual_host_port(
        container_port: int, env_var_name: str | None = None
    ) -> int | None:
        """Detect actual host port from environment variable.

        Args:
            container_port: The internal container port (e.g., 8501 for Streamlit)
            env_var_name: Environment variable name to check for port override

        Returns:
            The actual host port if found, None otherwise
        """
        # First check environment variable if provided
        if env_var_name:
            port_str = os.environ.get(env_var_name)
            if port_str:
                try:
                    return int(port_str)
                except (ValueError, TypeError):
                    pass

        # If no environment variable, return None
        # (we can't access docker-compose.override.yml from inside container)
        return None

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
        # Detect actual host port from environment variable if available
        actual_host_port = UICommands.detect_actual_host_port(
            port, env_var_name="STREAMLIT_HOST_PORT"
        )
        display_port = actual_host_port if actual_host_port else port

        # Docker環境での実行を考慮
        if host == "0.0.0.0":
            access_url = f"http://localhost:{display_port}"
        else:
            access_url = f"http://{host}:{display_port}"

        UICommands.show_progress("Starting Streamlit app with URL routing...")
        UICommands.show_progress(f"Access the app at: {access_url}")
        UICommands.show_progress("Available URLs:")
        UICommands.show_progress(f"  - {access_url}/             (Home)")
        UICommands.show_progress(f"  - {access_url}/meetings     (会議管理)")
        UICommands.show_progress(f"  - {access_url}/parties      (政党管理)")
        UICommands.show_progress(f"  - {access_url}/conferences  (会議体管理)")
        UICommands.show_progress("  ... and more")
        UICommands.show_progress("Press Ctrl+C to stop the server")
        UICommands.show_progress("")
        UICommands.show_progress("You can now view your Streamlit app in your browser.")
        UICommands.show_progress(f"  URL: {access_url}")

        # 新しいStreamlitアプリケーションを起動（Clean Architecture版）
        # browser.gatherUsageStatsをfalseにしてUsage statistics収集メッセージも抑制
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "src/interfaces/web/streamlit/app.py",  # Clean Architecture版に修正
                "--server.port",
                str(port),
                "--server.address",
                host,
                "--server.headless",
                "true",  # Dockerでの実行に必要
                "--browser.gatherUsageStats",
                "false",  # Usage statistics収集を無効化
                "--logger.level",
                "warning",  # INFOレベルのログを抑制
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
        # Detect actual host port from environment variable if available
        actual_host_port = UICommands.detect_actual_host_port(
            port, env_var_name="MONITORING_HOST_PORT"
        )
        display_port = actual_host_port if actual_host_port else port

        # Docker環境での実行を考慮
        if host == "0.0.0.0":
            access_url = f"http://localhost:{display_port}"
        else:
            access_url = f"http://{host}:{display_port}"

        UICommands.show_progress("Starting monitoring dashboard...")
        UICommands.show_progress(f"Access the dashboard at: {access_url}")
        UICommands.show_progress("Press Ctrl+C to stop the server")
        UICommands.show_progress("")
        UICommands.show_progress("You can now view your Streamlit app in your browser.")
        UICommands.show_progress(f"  URL: {access_url}")

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
                "--browser.gatherUsageStats",
                "false",  # Usage statistics収集を無効化
                "--logger.level",
                "warning",  # INFOレベルのログを抑制
            ]
        )


def get_ui_commands():
    """Get all UI-related commands"""
    return [UICommands.streamlit, UICommands.monitoring]
