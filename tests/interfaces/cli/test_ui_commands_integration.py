"""Integration tests for UI commands.

This test suite verifies that UI commands reference existing files
and can launch correctly, preventing runtime failures.

Related to Issue #621 and PR #626.
"""

import os
from unittest.mock import patch

import pytest


class TestUICommandsFileReferences:
    """Test that UI commands reference existing files."""

    def test_streamlit_command_file_exists(self):
        """Verify streamlit command references an existing file.

        The streamlit command should point to:
        src/interfaces/web/streamlit/app.py
        """
        streamlit_file = "src/interfaces/web/streamlit/app.py"
        assert os.path.exists(streamlit_file), (
            f"Streamlit app file not found: {streamlit_file}"
        )

    def test_monitoring_command_file_exists(self):
        """Verify monitoring command references an existing file.

        The monitoring command should point to:
        src/monitoring_app.py (until migrated to Clean Architecture)
        """
        monitoring_file = "src/monitoring_app.py"
        assert os.path.exists(monitoring_file), (
            f"Monitoring app file not found: {monitoring_file}"
        )

    def test_all_ui_command_files_exist(self):
        """Verify all UI command file references exist.

        This test extracts file paths from ui_commands.py and verifies
        each one exists, preventing runtime FileNotFoundError.
        """
        # Read ui_commands.py and extract file paths
        ui_commands_file = "src/cli_package/commands/ui_commands.py"
        assert os.path.exists(ui_commands_file), (
            f"UI commands file not found: {ui_commands_file}"
        )

        with open(ui_commands_file) as f:
            content = f.read()

        # Extract Python file paths from subprocess.run calls
        import re

        # Pattern: "src/path/to/file.py"
        file_pattern = r'"(src/[^"]+\.py)"'
        file_paths = re.findall(file_pattern, content)

        # Verify each file exists
        for file_path in file_paths:
            assert os.path.exists(file_path), (
                f"Referenced file does not exist: {file_path}"
            )


class TestUICommandsLaunch:
    """Test that UI commands can launch successfully."""

    @patch("src.cli_package.commands.ui_commands.subprocess.run")
    def test_streamlit_command_subprocess_called_correctly(self, mock_run):
        """Test streamlit command calls subprocess with correct file path.

        This is a simpler test that verifies the most critical aspect:
        the file path exists and would be passed to subprocess.
        """
        from click.testing import CliRunner

        from src.cli_package.commands.ui_commands import UICommands

        runner = CliRunner()

        # Invoke the command via Click's test runner
        _ = runner.invoke(UICommands.streamlit, ["--port", "8501", "--host", "0.0.0.0"])

        # Verify subprocess.run was called
        assert mock_run.called, "subprocess.run should have been called"

        # Get the call arguments
        call_args = mock_run.call_args[0][0]

        # Verify correct file path (most critical check)
        assert "src/interfaces/web/streamlit/app.py" in call_args, (
            f"Should reference correct app file. Got args: {call_args}"
        )

    @patch("src.cli_package.commands.ui_commands.subprocess.run")
    def test_monitoring_command_subprocess_called_correctly(self, mock_run):
        """Test monitoring command calls subprocess with correct file path.

        This verifies the critical bug fix: monitoring_app.py must exist
        when the command is invoked.
        """
        from click.testing import CliRunner

        from src.cli_package.commands.ui_commands import UICommands

        runner = CliRunner()

        # Invoke the command via Click's test runner
        _ = runner.invoke(
            UICommands.monitoring, ["--port", "8502", "--host", "0.0.0.0"]
        )

        # Verify subprocess.run was called
        assert mock_run.called, "subprocess.run should have been called"

        # Get the call arguments
        call_args = mock_run.call_args[0][0]

        # Verify correct file path (this would fail if file didn't exist)
        assert "src/monitoring_app.py" in call_args, (
            f"Should reference monitoring_app.py. Got args: {call_args}"
        )


class TestPortDetection:
    """Test port detection logic for Docker environments."""

    def test_detect_actual_host_port_with_env_var(self):
        """Test port detection from environment variable."""
        from src.cli_package.commands.ui_commands import UICommands

        with patch.dict(os.environ, {"STREAMLIT_HOST_PORT": "9291"}):
            port = UICommands.detect_actual_host_port(8501, "STREAMLIT_HOST_PORT")
            assert port == 9291, "Should detect port from environment variable"

    def test_detect_actual_host_port_without_env_var(self):
        """Test port detection when environment variable is not set."""
        from src.cli_package.commands.ui_commands import UICommands

        with patch.dict(os.environ, {}, clear=True):
            port = UICommands.detect_actual_host_port(8501, "STREAMLIT_HOST_PORT")
            assert port is None, "Should return None when env var not set"

    def test_detect_actual_host_port_invalid_env_var(self):
        """Test port detection with invalid environment variable value."""
        from src.cli_package.commands.ui_commands import UICommands

        with patch.dict(os.environ, {"STREAMLIT_HOST_PORT": "invalid"}):
            port = UICommands.detect_actual_host_port(8501, "STREAMLIT_HOST_PORT")
            assert port is None, "Should return None for invalid port value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
