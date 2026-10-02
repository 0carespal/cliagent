# 🤖 Autobot — Intelligent File & Folder Management CLI Agent

`Autobot` is an intelligent, cross-platform Command Line Interface (CLI) agent built in Python for locating, renaming, and moving files/folders across directory trees. Inspired by **Antigravity CLI** and **Aider**, it features a **persistent interactive REPL shell**, **tab auto-completion**, **first-class slash commands (`/`)**, **Antigravity-styled color theme**, **dry-run preview action cards**, **transaction history undo logs**, and **natural language AI processing** powered by Local LLMs (Gemma 4B / Qwen 4B) or Cloud LLMs (OpenAI, Groq, OpenRouter, DeepSeek, etc.).

---

## 🌟 Key Features

* **🔄 Persistent REPL Shell (`autobot › `)**: Continuous live terminal session powered by `prompt_toolkit`. Remembers working directory, active model provider, and undo history across inputs.
* **⚡ Tab Auto-Completion**: Context-aware completion for slash commands (`/lo` ➜ `/locate`, `/mo` ➜ `/models`) and local file system paths.
* **🎨 Antigravity CLI Theme**: Full ASCII box banner with rounded borders (`box.ROUNDED`), Cyan/Magenta/Slate color palette, and dynamic session status badges.
* **⚡ First-Class Slash Commands**: Predictable 0ms deterministic commands (`/locate`, `/rename`, `/move`, `/undo`, `/key`, `/model`, `/models`, `/status`, `/help`, `/clear`, `/exit`).
* **🔍 Hybrid Search Engine (Wildcard Glob + RapidFuzz)**: Precision `fnmatch` wildcard and glob matching (`*.png`, `*invoice*`, `doc_??.pdf`) with 100% precision score, combined with RapidFuzz fuzzy similarity scoring for natural typos (`invoce` ➜ `annual_invoice_2024.pdf`).
* **✏️ Case-Preserving Single & Bulk Rename**: Rename individual items or apply pattern transformations (`snake_case`, `kebab-case`, sequence numbering `01`, `02`). Safely handles case-only renames (`readme.md` ➜ `README.md`) on case-insensitive filesystems (Windows NTFS/FAT, macOS) using atomic two-step renaming without false collision errors.
* **🚚 Cross-Volume Safe Relocation & Guardrails**: Moves files seamlessly across drives and partitions with `shutil.move`. Verifies destination directories before moving; if missing, interactively prompts the user (`Create destination directory? [y/N]`).
* **📇 Action Cards & InquirerPy Confirmations**: Displays formatted Rich preview cards and interactive arrow-key confirmation menus (`[✓] Execute actions now` vs `[✖] Cancel operation`) before modifying disk. Supports `--yes` / `-y` flag for automated pipelines.
* **↩️ Cross-Drive Undo Subsystem (`/undo`)**: Logs every file operation to `~/.autobot/history.json`. Run `/undo` to interactively review and reverse the last transaction batch, even across different Windows drive letters (`C:\` to `D:\`).
* **⏳ Live Animated Spinners**: Renders Rich animated spinners (`⠋ Searching directory tree...`, `⠙ AI parsing natural language request...`) for fluid visual feedback.
* **🤖 Dual AI Engine (Local Ollama Auto-Discovery & Universal Cloud BYOK)**:
  - **Local Models**: Automatically queries `/v1/models` from local Ollama or LM Studio to auto-detect installed models (`qwen3.5`, `gemma4`, `llama3`). Switch dynamically with `/model list` and `/model <name>`.
  - **Cloud Models**: Bring-Your-Own-Key (BYOK) for any OpenAI-compatible provider (OpenAI, Groq, OpenRouter, DeepSeek, Mistral, Together, etc.) with `/key <API_KEY>` and persistent config in `~/.autobot/config.json`.
  - **Zero Assumptions**: Displays `[No model available]` cleanly until an AI engine is configured or detected.

---

## 🚀 Quick Start & Installation

### 1. Prerequisites
* Python 3.10 or higher installed on your system.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 💻 Interactive REPL & Slash Commands

Launch the interactive REPL shell by running `main.py` without arguments:

```bash
python main.py
```

### 🎯 Slash Command Cheat-Sheet

| Slash Command | Description | Example Usage |
| :--- | :--- | :--- |
| **`/locate`** | Locates files/folders matching wildcards (`*.png`) or fuzzy query | `/locate "*.pdf"` or `/locate "report"` |
| **`/rename`** | Renames a matching file or folder (supports case-only renames) | `/rename "readme.md" "README.md"` |
| **`/move`** | Moves matching files/folders to a target directory | `/move "*.png" "./Pictures"` |
| **`/undo`** | Reverses the last move or rename transaction session | `/undo` |
| **`/key`** | Views or configures your Cloud LLM API key | `/key sk-proj-...` |
| **`/model list`** (or **`/models`**) | Lists all detected local Ollama models and cloud model status | `/model list` |
| **`/model <name>`** | Switches active LLM model (e.g. `qwen3.5:4b`, `gemma4`, `cloud`) | `/model qwen3.5` or `/model cloud` |
| **`/status`** | Displays a summary card of active folder, model, and undo stack | `/status` |
| **`/help`** | Displays the interactive command cheat-sheet card | `/help` |
| **`/clear`** | Clears the terminal screen canvas | `/clear` |
| **`/exit`** | Exits the Autobot REPL session | `/exit` |

---

## 💬 Natural Language AI Commands

Type plain English sentences directly into the `autobot › ` prompt (or via `python main.py ask "..."`):

```text
autobot › find all PNG files in Downloads and move them to Pictures/PNGs
autobot › rename draft_document.txt to annual_report_2024.txt
autobot › move all reports larger than 10MB to Archive
```

---

## 🤖 AI Engine Setup (Local & Cloud)

### 1. Offline Local LLMs (Ollama / LM Studio)
`Autobot` runs 100% offline using **Ollama** or **LM Studio**:

1. Install and run [Ollama](https://ollama.ai) or LM Studio.
2. Pull your preferred model (e.g., `gemma2:4b` or `qwen2.5:4b`):
   ```bash
   ollama run gemma2:4b
   ```
3. `Autobot` automatically connects to `http://localhost:11434/v1` and routes natural language prompts locally!

### 2. Universal Cloud LLMs (BYOK — Bring Your Own Key)
Use any OpenAI-compatible provider (OpenAI, Groq, OpenRouter, DeepSeek, Mistral, Together, etc.).

* **Inside the interactive REPL**:
  ```text
  autobot › /key sk-your-api-key-here
  ```
  *(Saved automatically to `~/.autobot/config.json` so you only have to enter it once!)*

* **Or via environment variables**:
  ```bash
  # Windows PowerShell
  $env:LLM_API_KEY="your-api-key-here"
  $env:LLM_MODEL="gpt-4o-mini"            # Optional: defaults to gpt-4o-mini
  $env:LLM_BASE_URL="https://api.openai.com/v1"  # Optional: Groq/OpenRouter/etc.

  # Linux / macOS / Bash
  export LLM_API_KEY="your-api-key-here"
  export LLM_MODEL="gpt-4o-mini"
  export LLM_BASE_URL="https://api.openai.com/v1"
  ```

---

## 🧪 Running Automated Integration Tests

Run the full end-to-end integration test suite:

```bash
python tests/test_autobot.py
```

---

## 📁 Project Architecture

```text
cliagent/
├── agent.md              # Project Blueprint, Architecture & 19-Phase Roadmap
├── config.py             # System configuration, ignored folders, and LLM endpoints
├── main.py               # Main CLI launcher & Typer subcommand entry point
│
├── core/
│   ├── finder.py         # Recursive walker, rapidfuzz fuzzy search, & metadata filters
│   ├── renamer.py        # Single/bulk rename, pattern replacement, & case converters
│   ├── mover.py          # Safe file relocation & missing directory verification
│   ├── safety.py         # Rich preview table renderer & JSON transaction undo log
│   └── slash_commands.py # Quote-aware shlex parser & slash command router
│
├── ai/
│   ├── base.py           # System prompts & JSON response sanitization
│   ├── local_llm.py      # Ollama / LM Studio (Gemma/Qwen) HTTP client
│   ├── cloud_llm.py      # Universal Cloud LLM client (OpenAI, Groq, OpenRouter, etc.)
│   └── intent_parser.py  # Unified AI provider router & intent extractor
│
├── ui/
│   ├── theme.py          # Antigravity CLI palette, Option A box banner & status spinners
│   ├── repl.py           # Persistent REPL prompt loop with tab completion
│   ├── tables.py         # Rich search result formatting tables
│   └── interactive.py    # InquirerPy interactive confirmation selection dialogs
│
└── tests/
    └── test_autobot.py   # End-to-end automated integration test suite
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
