"""
Global Configuration Module for cliagent.
Defines system-wide constants, default ignored directories, and LLM connection settings.
"""
from pathlib import Path
import os

# Project Root Directory
BASE_DIR = Path(__file__).resolve().parent

# Default Ignored Directories (Junk / System / Dependency folders to prune during search)
DEFAULT_IGNORED_DIRS = {
    # Version Control & Package Managers
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "bower_components",
    # Python Caches & Virtual Envs
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "venv",
    ".venv",
    "env",
    ".env",
    "wheels",
    "*.egg-info",
    # Operating System & IDE Caches
    "AppData",
    "Local Settings",
    "Application Data",
    "$Recycle.Bin",
    "System Volume Information",
    ".idea",
    ".vscode",
    ".ds_store",
    "thumbs.db",
    "tmp",
    "temp",
}

# Transaction History Log File Path (for Undo functionality)
HISTORY_FILE_PATH = Path.home() / ".cliagent" / "history.json"

# Local LLM Defaults (Ollama / LM Studio)
LOCAL_LLM_URL = os.getenv("CLIAGENT_LOCAL_LLM_URL", "http://localhost:11434/v1")
LOCAL_LLM_MODEL = os.getenv("CLIAGENT_LOCAL_LLM_MODEL", "gemma2:4b")  # or qwen2.5:4b

# Cloud Gemini API Defaults
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
