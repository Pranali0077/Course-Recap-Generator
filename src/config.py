"""Configuration settings for Course Recap Generator."""

from pathlib import Path
import os
from dotenv import load_dotenv

# Base project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
DATA_DIR = PROJECT_ROOT / "data"
SKILLS_DIR = PROJECT_ROOT / ".gemini" / "skills"

# Load local environment variables from .env
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# Model configuration
DEFAULT_MODEL = "gemini-3.5-flash-lite"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def get_gemini_api_key() -> str:
    """Retrieve Gemini API key or raise helpful ValueError."""
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)
    key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Please set it in your environment or in a .env file."
        )
    return key
