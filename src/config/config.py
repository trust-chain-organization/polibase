"""
Configuration module for Polibase application

Loads and validates environment variables with proper type hints and error handling.
"""

import os
import subprocess

from dotenv import load_dotenv

from ..exceptions import InvalidConfigError, MissingConfigError


# Load environment variables
# Support custom .env path via POLIBASE_ENV_FILE environment variable
def find_env_file() -> str:
    """Find .env file, checking worktree main repo if local one doesn't exist"""
    custom_path = os.getenv("POLIBASE_ENV_FILE")
    if custom_path:
        return custom_path

    # Check local .env first
    if os.path.exists(".env"):
        return ".env"

    # Check if we're in a git worktree and look for main repo's .env
    try:
        # First, try to find the main worktree using porcelain format
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse porcelain output to find the first worktree (usually main)
        worktrees: list[dict[str, str | bool]] = []
        current_worktree: dict[str, str | bool] = {}
        for line in result.stdout.splitlines():
            if line.startswith("worktree "):
                if current_worktree:
                    worktrees.append(current_worktree)
                current_worktree = {"path": line.split()[1]}
            elif line.startswith("branch "):
                branch = line.split()[1]
                current_worktree["branch"] = branch
                # Check if this is the main branch
                if branch == "refs/heads/main":
                    current_worktree["is_main"] = True
        if current_worktree:
            worktrees.append(current_worktree)

        # Find main worktree
        for wt in worktrees:
            if wt.get("is_main"):
                path = wt.get("path")
                if isinstance(path, str):
                    main_env_path = os.path.join(path, ".env")
                    if os.path.exists(main_env_path):
                        return main_env_path

        # If no main branch found, use the first worktree (usually the original)
        if worktrees:
            path = worktrees[0].get("path")
            if isinstance(path, str):
                main_env_path = os.path.join(path, ".env")
                if os.path.exists(main_env_path):
                    return main_env_path

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return ".env"  # Fallback to local .env


ENV_FILE_PATH = find_env_file()
load_dotenv(ENV_FILE_PATH)

# LangChain Configuration
LANGCHAIN_TRACING_V2: str | None = os.getenv("LANGCHAIN_TRACING_V2")
LANGCHAIN_ENDPOINT: str | None = os.getenv("LANGCHAIN_ENDPOINT")
LANGCHAIN_API_KEY: str | None = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT: str | None = os.getenv("LANGCHAIN_PROJECT")

# API Keys
GOOGLE_API_KEY: str | None = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY: str | None = os.getenv("TAVILY_API_KEY")

# Database Configuration
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://polibase_user:polibase_password@localhost:5432/polibase_db",
)

# GCS Configuration
GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "polibase-scraped-minutes")
GCS_PROJECT_ID: str | None = os.getenv(
    "GCS_PROJECT_ID"
)  # Optional, uses default if not set
GCS_UPLOAD_ENABLED: bool = os.getenv("GCS_UPLOAD_ENABLED", "false").lower() == "true"


def validate_config() -> None:
    """Validate required configuration values"""
    # Check if Google API key is set when needed
    if not GOOGLE_API_KEY:
        import warnings

        warnings.warn(
            (
                "GOOGLE_API_KEY is not set. LLM features will not work. "
                "Please set it in your .env file or environment variables."
            ),
            RuntimeWarning,
            stacklevel=2,
        )

    # Validate DATABASE_URL format
    if not DATABASE_URL.startswith(("postgresql://", "postgres://")):
        raise InvalidConfigError(
            "DATABASE_URL must be a valid PostgreSQL connection string",
            {
                "current_value": DATABASE_URL[:30] + "..."
                if len(DATABASE_URL) > 30
                else DATABASE_URL
            },
        )


def set_env() -> None:
    """Set environment variables from loaded configuration"""
    env_vars: dict[str, str | None] = {
        "LANGCHAIN_TRACING_V2": LANGCHAIN_TRACING_V2,
        "LANGCHAIN_ENDPOINT": LANGCHAIN_ENDPOINT,
        "LANGCHAIN_API_KEY": LANGCHAIN_API_KEY,
        "LANGCHAIN_PROJECT": LANGCHAIN_PROJECT,
        "GOOGLE_API_KEY": GOOGLE_API_KEY,
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "TAVILY_API_KEY": TAVILY_API_KEY,
        "DATABASE_URL": DATABASE_URL,
    }

    for key, value in env_vars.items():
        if value is not None:
            os.environ[key] = value


def get_required_config(key: str) -> str:
    """Get a required configuration value or raise an error

    Args:
        key: The configuration key to retrieve

    Returns:
        The configuration value

    Raises:
        MissingConfigError: If the configuration is not set
    """
    value = globals().get(key)
    if value is None:
        raise MissingConfigError(
            f"Required configuration '{key}' is not set", {"key": key}
        )
    return value
