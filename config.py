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


def resolve_user_path(path_input: os.PathLike, base_dir: Path = None) -> Path:
    """
    Resolves user-entered path strings, expanding:
    - User home '~' (e.g. '~/Downloads' -> 'C:/Users/.../Downloads')
    - Standard OS folder aliases: 'Desktop', 'Downloads', 'Documents', 'Pictures', 'Music', 'Videos'
    - Relative paths against base_dir (defaults to Path.cwd())
    - Absolute paths
    """
    if isinstance(path_input, Path):
        p = path_input
    else:
        clean_str = str(path_input).strip("\"'")
        p = Path(clean_str)

    # Expand tilde ~
    p = p.expanduser()

    # Check for standard user directory aliases if single-segment or leading segment
    first_part = p.parts[0].lower() if p.parts else ""
    standard_aliases = {
        "desktop": Path.home() / "Desktop",
        "downloads": Path.home() / "Downloads",
        "documents": Path.home() / "Documents",
        "pictures": Path.home() / "Pictures",
        "music": Path.home() / "Music",
        "videos": Path.home() / "Videos",
    }

    if first_part in standard_aliases:
        alias_root = standard_aliases[first_part]
        if len(p.parts) > 1:
            p = alias_root.joinpath(*p.parts[1:])
        else:
            p = alias_root
        return p.resolve()

    if not p.is_absolute():
        base = base_dir if base_dir is not None else Path.cwd()
        return (base / p).resolve()

    return p.resolve()

