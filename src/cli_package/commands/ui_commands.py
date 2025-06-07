"""CLI commands for user interface operations"""
import click
import subprocess
import sys
from ..base import BaseCommand, with_error_handling


class UICommands(BaseCommand):
    """Commands for launching user interfaces"""
    
    @staticmethod
    @click.command()
    @click.option('--port', default=8501, help='Port number for Streamlit app')
    @click.option('--host', default='0.0.0.0', help='Host address')
    @with_error_handling
    def streamlit(port, host):
        """Launch Streamlit web interface for meeting management (会議管理Web UI)
        
        This command starts a web interface where you can:
        - View all registered meetings
        - Add new meetings with URLs and dates
        - Edit existing meeting information
        - Delete meetings
        - Manage political party member list URLs
        """
        # Docker環境での実行を考慮
        if host == '0.0.0.0':
            access_url = f"http://localhost:{port}"
        else:
            access_url = f"http://{host}:{port}"
        
        UICommands.show_progress(f"Starting Streamlit app...")
        UICommands.show_progress(f"Access the app at: {access_url}")
        UICommands.show_progress("Press Ctrl+C to stop the server")
        
        # Streamlitアプリケーションを起動
        subprocess.run([
            sys.executable, '-m', 'streamlit', 'run',
            'src/streamlit_app.py',
            '--server.port', str(port),
            '--server.address', host,
            '--server.headless', 'true'  # Dockerでの実行に必要
        ])


def get_ui_commands():
    """Get all UI-related commands"""
    return [
        UICommands.streamlit
    ]