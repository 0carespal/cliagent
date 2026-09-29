# Project Blueprint: CLI File Management Agent (`cliagent` / `Autobot`)

## 1. Executive Summary & Goal
`cliagent` (Autobot) is an intelligent, cross-platform CLI tool built in Python for locating, renaming, and moving files/folders across directory trees. It features **fuzzy searching**, **safety preview dry-run tables**, **transaction history logging (undo)**, and an **Antigravity-inspired interactive shell** supporting slash commands, tab auto-completion, and natural language command parsing powered by local LLMs (Gemma 4B / Qwen 4B) or cloud APIs (Gemini).

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
- **Undo / Transaction History System (`cliagent undo` / `/undo`)**:
  - Every non-dry-run operation logs its inverse action into a local JSON history log (`~/.autobot/history.json`).
  - Running `autobot undo` or `/undo` reads the last transaction log, confirms with the user, and reverses all file moves/renames.

---

## 3. Interaction Modes & UI/UX Standards

1. **Persistent REPL Shell Mode (`autobot › `)**:
   - Interactive live session loop powered by `prompt_toolkit` / `inquirerpy`.
   - Remembers working directory, active LLM model provider, and undo history count across inputs.
2. **Slash Command Router (`/`)**:
   - `/locate <query>` — Fuzzy search lookup
   - `/rename <query>` — Single or bulk rename
   - `/move <query> <target>` — File relocation
   - `/undo` — Revert last transaction session
   - `/model` — Toggle between local Gemma/Qwen and cloud Gemini
   - `/status` — View current session summary panel
   - `/clear` — Clear terminal screen
   - `/help` — Interactive command cheat-sheet card
   - `/exit` — Exit REPL loop
3. **Natural Language AI Mode**:
   - Accepts plain English instructions (e.g., `find all screenshot PNGs and move them to Pictures/Screenshots`).
   - Automatically generates a dry-run preview table and requires interactive confirmation (`Execute proposed actions? [y/N]`) before touching disk.
4. **Visual Theme (Antigravity CLI Palette)**:
   - **Primary Accent**: `bold cyan`
   - **Brand Highlights**: `bold magenta`
   - **Muted Paths**: `dim cyan` / `slate`
   - **Status Badges**: `bold yellow` (Model), `bold green` (Undo / Success)
   - **Banner**: Option A Full ASCII Box Banner with rounded borders (`box.ROUNDED`) and status bar metrics.
   - **Tab Auto-Completion**: Enabled for slash commands and local file paths.

---

## 4. Tech Stack

- **Language**: Python 3.10+
- **File System**: `pathlib` (cross-platform path objects), `shutil`, `os`
- **Fuzzy Search**: `rapidfuzz`
- **Terminal UI & Styling**: `rich`, `inquirerpy`, `prompt_toolkit`
- **CLI Parsing**: `typer`
- **Local LLM Integration**: OpenAI-compatible HTTP endpoint (`http://localhost:11434/v1` for Ollama or `http://localhost:1234/v1` for LM Studio) connecting to `Gemma 4B` or `Qwen 4B`.
- **Cloud LLM Integration**: Gemini API with configurable environment API key.

---

## 5. System Architecture & Module Structure

```text
cliagent/
│
├── agent.md              # Project Blueprint, Context & Roadmap (This file)
├── config.py             # User settings (API keys, local LLM URL, ignore lists)
│
├── core/
│   ├── finder.py         # Directory walker, fuzzy search engine, & property filters
│   ├── renamer.py        # Single/bulk rename & pattern transformation logic
│   ├── mover.py          # File/folder move engine & missing directory prompt
│   ├── safety.py         # Action plan builder, rich preview table, & undo JSON logger
│   └── slash_commands.py # [Phase 10] Slash command handlers & dispatcher
│
├── ai/
│   ├── base.py           # LLM provider interface
│   ├── local_llm.py      # Ollama / LM Studio client for Gemma/Qwen local models
│   ├── cloud_llm.py      # Cloud API client (Gemini)
│   └── intent_parser.py  # Unified AI provider router
│
├── ui/
│   ├── theme.py          # [Phase 8] Centralized Antigravity palette, banner & cards
│   ├── repl.py           # [Phase 9] Persistent REPL prompt loop with tab completion
│   ├── tables.py         # Terminal formatting & rich preview tables
│   └── interactive.py    # InquirerPy keypress confirmation dialogs
│
└── main.py               # Main CLI entry point, Typer parser & launcher
```

---

## 6. Implementation Roadmap

- [x] **Phase 1: Environment & Project Setup**: Directory skeleton, dependencies, & packaging.
- [x] **Phase 2: Core Finder Engine (`core/finder.py`)**: Fast recursive walker, fuzzy matching, folder pruning, & filters.
- [x] **Phase 3: Core Renamer Engine (`core/renamer.py`)**: Single and bulk rename operations & case converters.
- [x] **Phase 4: Core Mover Engine (`core/mover.py`)**: Moving files, destination verification, & missing directory prompt logic.
- [x] **Phase 5: Safety Subsystem (`core/safety.py`)**: Dry-run preview renderer (`rich` table) & undo log recorder/reverser.
- [x] **Phase 6: AI Intent Engine (`ai/`)**: System prompt design & JSON tool parser for Gemma/Qwen/Gemini.
- [x] **Phase 7: CLI Interface & Baseline UI (`main.py` & `ui/`)**: `typer` subcommands & Rich output tables.
- [x] **Phase 8: Centralized Theme & Styling Engine (`ui/theme.py`)**: Antigravity CLI color palette, Option A ASCII box banner renderer, Rich console tokens & error/warning cards.
- [x] **Phase 9: Persistent REPL Shell Loop (`ui/repl.py`)**: `autobot › ` interactive shell, session state retention, signal handling (`Ctrl+C`/`Ctrl+D`), non-TTY fallback, & tab auto-completion for slash commands and file paths.
- [ ] **Phase 10: Slash Command Router (`core/slash_commands.py`)**: Handlers for `/locate`, `/rename`, `/move`, `/undo`, `/model`, `/status`, `/help`, `/clear`, `/exit`.
- [ ] **Phase 11: Dynamic Header & Status Bar Integration**: Real-time status bar rendering in REPL and command outputs.
- [ ] **Phase 12: Interactive Action Cards & Confirmation Guardrails**: InquirerPy dry-run preview confirmation dialogs before disk changes.
- [ ] **Phase 13: Live Animated Spinners & AI Thinking States**: Rich spinners for directory search and AI intent parsing steps.
- [ ] **Phase 14: End-to-End Verification & Integration**: CLI integration tests, regression checks, and final polish.

---

## 7. Current Project Status

- **Status**: Phase 9 Completed. Ready for **Phase 10: Slash Command Router (`core/slash_commands.py`)**.
- **Last Action**: Built `ui/repl.py` (`autobot › ` prompt loop, command history logging in `~/.autobot/repl_history.txt`, tab auto-completer for slash commands and file paths, graceful signal handling, non-TTY TTY fallback).

