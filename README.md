# 🤖 Autobot — Intelligent File & Folder Management CLI Agent

`Autobot` is an intelligent, cross-platform Command Line Interface (CLI) agent built in Python for locating, renaming, and moving files/folders across directory trees. It features **fuzzy string search**, **dry-run preview tables**, **transaction history undo logs**, and a **hybrid interface** supporting CLI flags, interactive menus, and natural language command processing via Local LLMs (**Gemma 4B / Qwen 4B**) or Cloud Gemini.

---

## 🌟 Key Features

* **🔍 Smart Fuzzy Search**: Locates files/folders across directories using similarity scoring (`rapidfuzz`). Typing `invoice` matches `Annual_Invoice_2024.pdf`.
* **⚡ In-Place Directory Pruning**: Automatically skips scanning junk/system folders (`.git`, `node_modules`, `AppData`, `__pycache__`, `$Recycle.Bin`) for lightning-fast performance.
* **✏️ Single & Bulk Rename**: Rename individual items or apply pattern transformations (prefix, suffix, find & replace, sequence numbering like `01`, `02`, `snake_case`, `kebab-case`).
* **🚚 Destination Folder Protection**: Verifies target destination directories. If a target folder is missing, `Autobot` halts and prompts: *"Destination directory does not exist. Create folder? [y/N]"*. It creates folders **only** if confirmed with `y` or `Y`.
* **🔍 Dry-Run Preview Mode (`--dry-run`)**: Displays a color-coded Rich table of proposed actions, source/target paths, and warnings without touching your disk.
* **↩️ Transaction History & Undo (`autobot undo`)**: Automatically logs file operations to `~/.autobot/history.json`. Run `python main.py undo` to reverse the last move or rename batch.
* **🤖 Natural Language AI Engine (`autobot ask`)**: Accepts plain English sentences and converts them into structured actions using local Ollama/LM Studio LLMs (`Gemma 4B`, `Qwen 4B`) or Cloud Gemini APIs.

---

## 🚀 Quick Start & Installation

### 1. Prerequisites
* Python 3.10 or higher installed on your system.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 💻 Usage & Command Reference

### 1. Locate / Search Files & Folders
Search recursively from any starting directory with optional extension or size filters:
```bash
# Basic search
python main.py locate "report"

# Search in specific directory with extension filter
python main.py locate "invoice" --start-dir "~/Downloads" --ext pdf png
```

### 2. Move Files / Folders
Move files to a target directory with optional dry-run preview:
```bash
# Preview move actions without modifying disk
python main.py move "report" "./Archive" --dry-run

# Execute move
python main.py move "report" "./Archive"
```

### 3. Rename Files / Folders
Single or bulk rename with case formatting or sequence numbering:
```bash
# Single rename
python main.py rename "old_draft.txt" --new-name "final_report.txt"

# Bulk rename with prefix and snake_case formatting
python main.py rename "document" --prefix "2024_" --case "snake"

# Sequence numbering (photo_01.jpg, photo_02.jpg)
python main.py rename "IMG" --seq "photo_"
```

### 4. Natural Language AI Assistant (`ask`)
Talk to `Autobot` in plain English:
```bash
python main.py ask "Find all PNG files in Downloads and move them to Pictures/PNGs"
```

### 5. Undo Last Operation
Reverse the last batch move or rename transaction:
```bash
python main.py undo
```

### 6. Interactive Menu Mode
Run `Autobot` with no arguments to launch the interactive terminal menu:
```bash
python main.py
```

---

## 🤖 Local LLM Setup (Gemma 4B / Qwen 4B)

`Autobot` supports offline local AI execution via **Ollama** or **LM Studio**:

1. Install and run [Ollama](https://ollama.ai) or LM Studio.
2. Pull a 4B model (e.g., `gemma2:4b` or `qwen2.5:4b`):
   ```bash
   ollama run gemma2:4b
   ```
3. `Autobot` automatically detects the local OpenAI-compatible endpoint at `http://localhost:11434/v1` and routes natural language prompts to your local model!

*(Optional)* To use Cloud Gemini instead, set your API key environment variable:
```bash
set GEMINI_API_KEY="your-api-key-here"
```

---

## 📁 Project Architecture

```text
cliagent/
├── config.py             # System configuration, ignored folders, and LLM endpoints
├── core/
│   ├── finder.py         # Directory walker, rapidfuzz fuzzy search, & metadata filters
│   ├── renamer.py        # Single/bulk rename, pattern replacement, & collision check
│   ├── mover.py          # Safe file relocation & missing directory prompt logic
│   └── safety.py         # Rich dry-run preview renderer & JSON transaction undo log
├── ai/
│   ├── base.py           # System prompts & JSON response sanitization
│   ├── local_llm.py      # Ollama / LM Studio (Gemma/Qwen) HTTP client
│   ├── cloud_llm.py      # Cloud Gemini API client
│   └── intent_parser.py  # Unified AI provider router
├── ui/
│   ├── tables.py         # Rich terminal tables & file size formatters
│   └── interactive.py    # Terminal prompts & fallback main menu
└── main.py               # Main CLI entry point & Typer subcommand parser
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
