from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"


def load_project_env(override: bool = False) -> None:
    """Load the project's .env file when present."""
    if ENV_FILE.exists():
        load_dotenv(dotenv_path=ENV_FILE, override=override)
