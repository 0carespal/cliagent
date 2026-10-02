# Project Blueprint: CLI File Management Agent (`cliagent` / `Autobot`)

## 1. Executive Summary & Goal
`cliagent` (Autobot) is an intelligent, cross-platform CLI tool built in Python for locating, renaming, and moving files/folders across directory trees. It features **fuzzy searching**, **safety preview dry-run tables**, **transaction history logging (undo)**, and an **Antigravity-inspired interactive shell** supporting slash commands, tab auto-completion, and natural language command parsing powered by local LLMs (Gemma 4B / Qwen 4B) or universal cloud LLMs (OpenAI, Groq, OpenRouter, DeepSeek, etc.).

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
   - `/key` — View or set Cloud LLM API key
   - `/model` — Toggle between local Gemma/Qwen and cloud LLM
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
- **Cloud LLM Integration**: Universal OpenAI-compatible API (OpenAI, Groq, OpenRouter, DeepSeek, Mistral, etc.) with configurable API key (`LLM_API_KEY`).

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
│   ├── cloud_llm.py      # Universal Cloud LLM API client (OpenAI, Groq, OpenRouter, etc.)
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
- [x] **Phase 6: AI Intent Engine (`ai/`)**: System prompt design & JSON tool parser for Gemma/Qwen/Cloud LLMs.
- [x] **Phase 7: CLI Interface & Baseline UI (`main.py` & `ui/`)**: `typer` subcommands & Rich output tables.
- [x] **Phase 8: Centralized Theme & Styling Engine (`ui/theme.py`)**: Antigravity CLI color palette, Option A ASCII box banner renderer, Rich console tokens & error/warning cards.
- [x] **Phase 9: Persistent REPL Shell Loop (`ui/repl.py`)**: `autobot › ` interactive shell, session state retention, signal handling (`Ctrl+C`/`Ctrl+D`), non-TTY fallback, & tab auto-completion for slash commands and file paths.
- [x] **Phase 10: Slash Command Router (`core/slash_commands.py`)**: Token parsing (`shlex`), handlers for `/locate`, `/rename`, `/move`, `/undo`, `/model`, `/status`, `/help`, `/clear`, `/exit`.
- [x] **Phase 11: Dynamic Header & Status Bar Integration**: Wired `main.py` launcher to `AutobotREPL`, dual slash-command/AI input router, stream reconfigure, and unified Typer subcommands.
- [x] **Phase 12: Interactive Action Cards & Confirmation Guardrails (`ui/interactive.py`)**: Built `InquirerPy` confirmation selection cards with Rich fallbacks for action execution, missing folder prompts, and undo session reversals.
- [x] **Phase 13: Live Animated Spinners & AI Thinking States**: Added `AutobotTheme.status()` context manager wrapping directory search, file relocation, and AI intent parsing steps with live animated spinners.
- [x] **Phase 14: End-to-End Verification & Integration (`tests/test_autobot.py`)**: Built automated integration test suite validating fuzzy search, single rename, file relocation, transaction log undo rollback, and SlashCommandRouter dispatching.
- [x] **Phase 15: Universal Cloud LLM (BYOK), Dynamic Model Detection & Config Persistence**: Replaced vendor-locked Gemini REST calls with a universal OpenAI-compatible adapter supporting any cloud provider, added tiered config persistence (`~/.autobot/config.json`), `/key` command, and dynamic detection displaying `[No model available]` until configured.
- [x] **Phase 16: Interactive Safety Guardrails & Missing Folder Verification**: Wired `InteractiveUI` confirmation dialogs into `/rename`, `/move`, and natural language AI commands; prompt and create missing target directories upon user consent; require confirmation before undo rollback; supported `--yes`/`-y` automated execution flag.
- [x] **Phase 17: Local Ollama Model Auto-Discovery & Dynamic Model Switching (`/model list`)**: Automatically query `/v1/models` from local Ollama/LM Studio to detect installed models, enhance `/model list` and `/model <name>` to select installed models, and provide actionable AI configuration guidance.
- [x] **Phase 18: Search Engine Precision (Fnmatch Wildcard / Glob Matching)**: Integrate `fnmatch` into `FileFinder._compute_score` so wildcard patterns (`*.png`, `*invoice*`) receive 100% match scores instead of fuzzy penalties.
- [x] **Phase 19: Windows Cross-Drive Undo & Case-Preserving Renaming**: Replace `Path.rename` with `shutil.move` in `core/safety.py` for cross-volume reliability, and handle case-only renaming on case-insensitive filesystems.
- [x] **Phase 20: Smart Path Alias Resolution, REPL AI Workspace Awareness & camelCase Renaming**: Centralized `resolve_user_path` resolving `~`, `Desktop`, `Downloads`, `Documents`, etc. against active REPL workspace `repl_instance.cwd`; added `cwd_override` to `ask_command` so AI natural language prompts execute in current folder; added `camel` and `title` case bulk transformation support; updated `/cd` slash command and test suite (12 unit tests passing).
- [x] **Phase 21: AI Parsing Resilience & Transaction History Viewer**: Robust JSON extraction in `ai/base.py` (braced extraction `{ ... }` and regex fence stripping), Cloud LLM fallback retry without `response_format` on 400 Bad Request, `get_history` helper in `core/safety.py`, `render_history_table` in `ui/tables.py`, `/history` slash command and `autobot history` Typer CLI command (15 unit tests passing).

---

## 7. Current Project Status

- **Completed Phases**: Phases 1 through 21 (100% verified & tested).
- **Next Phase**: Production deployment, user manual polish, and release tagging.
- **Last Action**: Completed Phase 21 (Resilient JSON intent extraction, Cloud LLM fallback retry on HTTP 400, transaction history inspector across CLI and REPL, automated test suite expanded to 15 passing tests).







