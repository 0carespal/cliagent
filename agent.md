# Project Blueprint: CLI File Management Agent (`cliagent`)

## 1. Executive Summary & Goal
`cliagent` is an intelligent, cross-platform CLI tool built in Python for locating, renaming, and moving files/folders across directories. It features fuzzy searching, safety preview (dry-run) modes, transaction history logging (undo), and a hybrid interface supporting traditional CLI flags, interactive menus, and natural language command parsing powered by local LLMs (Gemma 4B / Qwen 4B) or cloud APIs (Gemini).

---

## 2. Core Functional Requirements

### A. Locate & Search Engine
- **Search Matching**: Fast recursive directory search using **Fuzzy Matching** (`rapidfuzz`) to catch partial/imprecise queries (e.g. searching `report` finds `annual_report_2024.pdf`).
- **Ignored Directories**: Automatic exclusion of system, cache, and dependency folders (`.git`, `node_modules`, `AppData`, `__pycache__`, `$Recycle.Bin`, `System32`, `env`, `.venv`).
- **Filters**: Support optional filtering by extension (`.png`, `.pdf`), file size (`> 50MB`), and modification date.
- **Output**: Returns absolute paths and locations cleanly in terminal.

### B. Renamer Engine
- **Single Rename**: Renaming individual files/folders with collision checks.
- **Bulk Rename**: Pattern-based mass renaming (e.g., prefixing `2024_`, numbering `photo_01.jpg`, changing extension `.jpeg` -> `.jpg`).
- **Case Transformations**: Options for `snake_case`, `kebab-case`, `camelCase`, and `lowercase`.

### C. Mover Engine & Target Destination Safety
- **Safe Relocation**: Moves single or multiple files/folders to target destinations.
- **Missing Target Folder Prompt**: If the destination folder does not exist:
  - Do **NOT** create it automatically.
  - Halt and prompt the user: `Destination folder '<path>' does not exist. Create folder? [y/N]`.
  - Create the directory **ONLY** if the user inputs `y` or `Y`.

### D. Safety Subsystem
- **View-Only / Dry-Run Mode (`--dry-run` or `-d`)**:
  - Prepares an execution plan in memory.
  - Displays a formatted, color-coded preview table using `rich` showing actions, source paths, target paths, and warnings (`OK`, `Collision Warning`, `Missing Target Folder`).
  - Exits without modifying disk if dry-run flag is active.
- **Undo / Transaction History System (`cliagent undo`)**:
  - Every non-dry-run operation logs its inverse action into a local JSON history log (`~/.cliagent/history.json`).
  - Running `cliagent undo` reads the last transaction log, confirms with the user, and reverses all file moves/renames.

---

## 3. Interaction Modes (Hybrid Architecture)

1. **CLI Flag Mode**: Fast Unix/Windows-style commands (e.g., `cliagent locate "invoice" --ext pdf`).
2. **Interactive Menu Mode**: Running `cliagent` with no flags launches a terminal UI with numbered options and interactive selection prompts.
3. **Natural Language AI Mode (`cliagent ask "..."`)**: Passes plain English instructions to an LLM (Local Ollama/LM Studio running Gemma 4B / Qwen 4B or Cloud Gemini API), which parses user intent into structured JSON actions for execution.

---

## 4. Tech Stack

- **Language**: Python 3.10+
- **File System**: `pathlib` (cross-platform path objects), `shutil`, `os`
- **Fuzzy Search**: `rapidfuzz`
- **Terminal UI & Tables**: `rich`, `inquirerpy` / `prompt_toolkit`
- **CLI Parsing**: `argparse` / `click` / `typer`
- **Local LLM Integration**: OpenAI-compatible HTTP endpoint (`http://localhost:11434/v1` for Ollama or `http://localhost:1234/v1` for LM Studio) connecting to local `Gemma 4B` or `Qwen 3.5/2.5 4B`.
- **Cloud LLM Integration**: Gemini API (`google-genai` SDK) with configurable API key.

---

## 5. System Architecture & Module Structure

```text
cliagent/
│
├── agent.md              # Project Blueprint & Context (This file)
├── config.py             # User settings (API keys, local LLM URL, ignore lists)
│
├── core/
│   ├── finder.py         # Directory walker, fuzzy search engine, & property filters
│   ├── renamer.py        # Single/bulk rename & pattern transformation logic
│   ├── mover.py          # File/folder move engine & missing directory prompt
│   └── safety.py         # Action plan builder, rich preview table, & undo JSON logger
│
├── ai/
│   ├── base.py           # LLM provider interface
│   ├── local_llm.py      # Ollama / LM Studio client for Gemma/Qwen local models
│   └── cloud_llm.py      # Cloud API client (Gemini)
│
├── ui/
│   ├── tables.py         # Terminal formatting & rich tables
│   └── interactive.py    # Interactive fallback menus
│
└── main.py               # Main CLI entry point & argument parser
```

---

## 6. Implementation Roadmap

- [x] **Phase 1: Environment & Project Setup**: Directory skeleton, dependencies, & packaging.
- [x] **Phase 2: Core Finder Engine (`core/finder.py`)**: Fast recursive walker, fuzzy matching, folder pruning, & filters.
- [x] **Phase 3: Core Renamer Engine (`core/renamer.py`)**: Single and bulk rename operations & case converters.
- [x] **Phase 4: Core Mover Engine (`core/mover.py`)**: Moving files, destination verification, & missing directory prompt logic.
- [ ] **Phase 5: Safety Subsystem (`core/safety.py`)**: Dry-run preview renderer (`rich` table) & undo log recorder/reverser.
- [ ] **Phase 6: AI Intent Engine (`ai/`)**: System prompt design & JSON tool parser for Gemma/Qwen/Gemini.
- [ ] **Phase 7: CLI Interface & Hybrid UI (`main.py` & `ui/`)**: `argparse` CLI commands, interactive menu fallback, & entry point wiring.

---

## 7. Current Project Status

- **Status**: Phase 4 Completed. Ready for **Phase 5: Safety Subsystem (`core/safety.py`)**.
- **Last Action**: Implemented `FileMover` in `core/mover.py` with `MoveAction` validation, destination directory check (`MISSING_DESTINATION`), user prompt helper `create_destination_directory(target_dir, user_confirmed)`, cross-volume support (`shutil.move`), and git commit.
