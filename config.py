"""
Global Configuration Module for Autobot.
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
HISTORY_FILE_PATH = Path.home() / ".autobot" / "history.json"

# Config Directory & File Path (for user settings persistence)
CONFIG_DIR = Path.home() / ".autobot"
CONFIG_FILE_PATH = CONFIG_DIR / "config.json"


def load_user_config() -> dict:
    """Loads persistent user configuration from ~/.autobot/config.json."""
    if CONFIG_FILE_PATH.exists():
        try:
            import json
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_user_config(key: str, value: str) -> None:
    """Persists a configuration key-value pair to ~/.autobot/config.json."""
    import json
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = load_user_config()
    cfg[key] = value
    with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


_user_cfg = load_user_config()

# Local LLM Defaults (Ollama / LM Studio)
LOCAL_LLM_URL = os.getenv("AUTOBOT_LOCAL_LLM_URL", os.getenv("CLIAGENT_LOCAL_LLM_URL", "http://localhost:11434/v1"))
LOCAL_LLM_MODEL = os.getenv("AUTOBOT_LOCAL_LLM_MODEL", os.getenv("CLIAGENT_LOCAL_LLM_MODEL", "gemma2:4b"))  # or qwen2.5:4b

# Cloud LLM Defaults (Universal OpenAI-compatible API: OpenAI, Groq, OpenRouter, DeepSeek, Mistral, etc.)
LLM_API_KEY = os.getenv(
    "LLM_API_KEY",
    os.getenv("AUTOBOT_API_KEY", os.getenv("OPENAI_API_KEY", _user_cfg.get("llm_api_key", "")))
)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", _user_cfg.get("llm_base_url", "https://api.openai.com/v1"))
LLM_MODEL = os.getenv("LLM_MODEL", _user_cfg.get("llm_model", "gpt-4o-mini"))

