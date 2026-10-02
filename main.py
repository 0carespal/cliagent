"""
Main Entry Point and Launcher for Autobot CLI.
Launches the persistent Antigravity-style REPL shell when run with no arguments,
or parses Typer subcommands for direct CLI execution.
"""

import sys
import io
from pathlib import Path
from typing import List, Optional
import typer

from ui.theme import AutobotTheme
from ui.repl import AutobotREPL
from ui.tables import TableRenderer
from ui.interactive import InteractiveUI
from core.finder import FileFinder
from core.renamer import FileRenamer
from core.mover import FileMover
from core.safety import TransactionLogger, PlanRenderer
from core.slash_commands import SlashCommandRouter
from ai.intent_parser import AIIntentParser
from config import resolve_user_path

# Ensure UTF-8 encoding on Windows console streams safely
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

app = typer.Typer(help="🤖 Autobot — Intelligent File & Folder Management CLI Agent")
console = AutobotTheme.get_console()
finder = FileFinder()
renamer = FileRenamer()
mover = FileMover()
logger = TransactionLogger()
slash_router = SlashCommandRouter()


@app.command("locate")
def locate_command(
    query: str = typer.Argument(..., help="Search query or wildcard filename pattern"),
    start_dir: str = typer.Option(".", "--start-dir", "-s", help="Root directory to start search"),
    min_score: float = typer.Option(60.0, "--min-score", "-m", help="Minimum match score (0-100)"),
    ext: Optional[List[str]] = typer.Option(None, "--ext", "-e", help="File extension filters (e.g. pdf png)"),
    min_size_mb: Optional[float] = typer.Option(None, "--min-size", help="Minimum file size in MB"),
    max_size_mb: Optional[float] = typer.Option(None, "--max-size", help="Maximum file size in MB"),
    type: str = typer.Option("all", "--type", "-t", help="Target type: files, folders, all"),
):
    """
    🔍 Locates files or folders matching a query across directories with fuzzy matching.
    """
    resolved_start = str(resolve_user_path(start_dir))
    console.print(f"[cyan]Searching for:[/cyan] '{query}' in [bold]{resolved_start}[/bold]...")
    try:
        results = finder.search(
            query=query,
            start_dir=resolved_start,
            min_score=min_score,
            extensions=ext,
            min_size_mb=min_size_mb,
            max_size_mb=max_size_mb,
            search_type=type
        )
        TableRenderer.render_search_results(results, query)
    except Exception as e:
        AutobotTheme.render_error(f"Search error: {e}")


@app.command("rename")
def rename_command(
    query: str = typer.Argument(..., help="Search query or file to rename"),
    new_name: Optional[str] = typer.Option(None, "--new-name", "-n", help="New filename for single rename"),
    prefix: Optional[str] = typer.Option(None, "--prefix", "-p", help="Prefix for bulk rename"),
    suffix: Optional[str] = typer.Option(None, "--suffix", "-s", help="Suffix for bulk rename"),
    case: Optional[str] = typer.Option(None, "--case", "-c", help="Case conversion: snake, kebab, camel, title, lower, upper"),
    seq: Optional[str] = typer.Option(None, "--seq", help="Sequence pattern: e.g. photo_"),
    start_dir: str = typer.Option(".", "--start-dir", help="Directory to search for items to rename"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Preview proposed actions without modifying disk"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Execute immediately without confirmation prompt"),
):
    """
    ✏️ Renames single or multiple files/folders matching a query.
    """
    try:
        resolved_start = str(resolve_user_path(start_dir))
        if new_name:
            actions = renamer.prepare_single_rename(query=query, new_name=new_name, start_dir=resolved_start)
        elif any([prefix, suffix, case, seq]):
            actions = renamer.prepare_bulk_rename(
                query=query, start_dir=resolved_start, prefix=prefix, suffix=suffix, case_type=case, seq_pattern=seq
            )
        else:
            AutobotTheme.render_warning("Specify --new-name or bulk pattern flags (--prefix, --suffix, --case, --seq).")
            return

        if not actions:
            AutobotTheme.render_warning(f"No files matching '{query}' found to rename.")
            return

        # Interactive confirmation guardrail
        if not InteractiveUI.confirm_action_execution(actions, dry_run=dry_run, yes=yes):
            return

        executed, errors = renamer.execute_rename(actions)
        if executed:
            session_id = logger.log_session(executed)
            AutobotTheme.render_success(f"Renamed {len(executed)} item(s)! Logged in session [dim]{session_id}[/dim]")
        if errors:
            for err in errors:
                AutobotTheme.render_error(err)
    except Exception as e:
        AutobotTheme.render_error(f"Rename error: {e}")


@app.command("move")
def move_command(
    query: str = typer.Argument(..., help="Search query or wildcard for items to move"),
    target_dir: str = typer.Argument(..., help="Destination target directory path"),
    start_dir: str = typer.Option(".", "--start-dir", "-s", help="Directory to search for items to move"),
    ext: Optional[List[str]] = typer.Option(None, "--ext", "-e", help="Extension filters"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Preview proposed actions without modifying disk"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Execute immediately without confirmation prompt"),
):
    """
    🚚 Moves single or multiple files/folders to a target directory.
    """
    try:
        resolved_start = str(resolve_user_path(start_dir))
        resolved_target = str(resolve_user_path(target_dir, base_dir=Path(resolved_start)))
        actions = mover.prepare_move(query=query, target_dir=resolved_target, start_dir=resolved_start, extensions=ext)
        if not actions:
            AutobotTheme.render_warning(f"No files matching '{query}' found to move.")
            return

        # Check if destination directory is missing
        missing_dest = any(a.requires_dest_creation or a.status == "MISSING_DESTINATION" for a in actions)
        if missing_dest:
            dest_path = Path(resolved_target)
            if not dest_path.exists():
                if InteractiveUI.prompt_create_destination(dest_path, yes=yes):
                    mover.create_destination_directory(dest_path, user_confirmed=True)
                    for a in actions:
                        if a.status == "MISSING_DESTINATION":
                            a.status = "OK"
                            a.message = "Destination created. Ready to move."
                else:
                    AutobotTheme.render_warning("Destination creation cancelled. Move operation aborted.")
                    return

        # Interactive confirmation guardrail
        if not InteractiveUI.confirm_action_execution(actions, dry_run=dry_run, yes=yes):
            return

        executed, errors = mover.execute_move(actions)
        if executed:
            session_id = logger.log_session(executed)
            AutobotTheme.render_success(f"Moved {len(executed)} item(s) to '{resolved_target}'! Session: [dim]{session_id}[/dim]")
        if errors:
            for err in errors:
                AutobotTheme.render_error(err)
    except Exception as e:
        AutobotTheme.render_error(f"Move error: {e}")


@app.command("ask")
def ask_command(
    prompt: str = typer.Argument(..., help="Natural language request"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Preview proposed actions without executing"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Execute immediately without confirmation prompt"),
    cwd_override: Optional[Path] = typer.Option(None, "--cwd", hidden=True, help="Internal directory override"),
):
    """
    🤖 Natural language AI assistant powered by Local LLMs (Gemma/Qwen 4B) or Cloud LLMs (OpenAI, Groq, OpenRouter, etc.).
    """
    ai_parser = AIIntentParser()
    with AutobotTheme.status(f"AI parsing natural language request: '{prompt}'..."):
        intent_data, provider_name = ai_parser.parse(prompt)

    if not intent_data:
        AutobotTheme.render_error(f"AI Engine failed to parse request using provider: {provider_name}")
        AutobotTheme.render_warning("💡 Tip: Use /key <api_key> to configure a Cloud LLM key, or start a local Ollama instance.")
        return

    AutobotTheme.render_success(f"Intent Parsed using provider: {provider_name}")
    action = intent_data.get("action")
    query = intent_data.get("query", "*")
    source_dir = intent_data.get("source_dir") or "."
    target_dir = intent_data.get("target_dir")
    new_name = intent_data.get("new_name")
    filters = intent_data.get("filters") or {}
    exts = filters.get("extensions")

    effective_base = cwd_override or Path.cwd()
    resolved_source = str(resolve_user_path(source_dir, base_dir=effective_base))
    resolved_target = str(resolve_user_path(target_dir, base_dir=Path(resolved_source))) if target_dir else None

    if action == "locate":
        locate_command(query=query, start_dir=resolved_source, ext=exts)
    elif action == "rename":
        if not new_name:
            AutobotTheme.render_error("AI error: Missing target rename name.")
            return
        rename_command(query=query, new_name=new_name, start_dir=resolved_source, dry_run=dry_run, yes=yes)
    elif action == "move":
        if not resolved_target:
            AutobotTheme.render_error("AI error: Missing target move directory.")
            return
        move_command(query=query, target_dir=resolved_target, start_dir=resolved_source, ext=exts, dry_run=dry_run, yes=yes)
    else:
        AutobotTheme.render_warning(f"Unknown action parsed by AI: {action}")


@app.command("undo")
def undo_command(
    yes: bool = typer.Option(False, "--yes", "-y", help="Execute undo immediately without confirmation prompt"),
):
    """
    ↩️ Reverses the last move or rename transaction session.
    """
    last = logger.get_last_session()
    if not last:
        AutobotTheme.render_warning("No transaction history found to undo.")
        return

    session_id = last.get("session_id", "unknown")
    records_count = len(last.get("records", []))

    if not InteractiveUI.prompt_undo_confirmation(session_id, records_count, yes=yes):
        AutobotTheme.render_warning("Undo operation cancelled by user.")
        return

    console.print(f"[cyan]Undoing session:[/cyan] [bold]{session_id}[/bold] ({records_count} actions)...")
    reversed_count, errors = logger.undo_last_session()

    if reversed_count > 0:
        AutobotTheme.render_success(f"Successfully restored {reversed_count} file(s) to original state!")
    if errors:
        for err in errors:
            AutobotTheme.render_error(err)


def repl_input_handler(user_input: str, repl_instance: AutobotREPL) -> None:
    """
    Dispatches input received inside the REPL loop:
    1. First checks if input is a slash command (/locate, /rename, /move, /undo, /model, /status, /help).
    2. If not a slash command, routes input to AI Intent Parser for natural language processing.
    """
    # Attempt to handle as slash command
    if slash_router.dispatch(user_input, repl_instance):
        return

    # Fallback to AI Natural Language Assistant
    ask_command(prompt=user_input, cwd_override=repl_instance.cwd)


def main_launcher():
    """
    Launcher: If no CLI subcommands are passed, launches the persistent Autobot REPL session loop.
    """
    if len(sys.argv) == 1:
        repl = AutobotREPL(handler_callback=repl_input_handler)
        repl.run()
    else:
        app()


if __name__ == "__main__":
    main_launcher()
