import sys
import io

# Force UTF-8 encoding on Windows terminal streams
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from pathlib import Path
from typing import List, Optional
import typer
from rich.console import Console

from core.finder import FileFinder
from core.renamer import FileRenamer, RenameAction
from core.mover import FileMover, MoveAction
from core.safety import TransactionLogger, PlanRenderer
from ai.intent_parser import AIIntentParser
from ui.tables import TableRenderer
from ui.interactive import InteractiveUI

app = typer.Typer(help="🤖 Autobot — Intelligent File & Folder Management CLI Agent")
console = Console()
finder = FileFinder()
logger = TransactionLogger()


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
    console.print(f"[cyan]Searching for:[/cyan] '{query}' in [bold]{start_dir}[/bold]...")
    try:
        results = finder.search(
            query=query,
            start_dir=start_dir,
            min_score=min_score,
            extensions=ext,
            min_size_mb=min_size_mb,
            max_size_mb=max_size_mb,
            search_type=type
        )
        TableRenderer.render_search_results(results, query)
    except Exception as e:
        console.print(f"[bold red]Error during search: {e}[/bold red]")


@app.command("rename")
def rename_command(
    query: str = typer.Argument(..., help="Search query or file to rename"),
    new_name: Optional[str] = typer.Option(None, "--new-name", "-n", help="New filename (for single rename)"),
    prefix: str = typer.Option("", "--prefix", help="Prefix to add to filenames"),
    suffix: str = typer.Option("", "--suffix", help="Suffix to add to filenames"),
    find_str: str = typer.Option("", "--find", help="Substring to find"),
    replace_str: str = typer.Option("", "--replace", help="Replacement substring"),
    case: Optional[str] = typer.Option(None, "--case", "-c", help="Case conversion: snake, kebab, lower, upper"),
    seq_prefix: Optional[str] = typer.Option(None, "--seq", help="Sequence numbering prefix (e.g. 'photo_')"),
    start_dir: str = typer.Option(".", "--start-dir", "-s", help="Directory to search in"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Preview proposed actions without executing"),
):
    """
    ✏️ Renames single or multiple files/folders matching a query.
    """
    results = finder.search(query=query, start_dir=start_dir)
    if not results:
        console.print(f"[yellow]No items found matching '{query}'.[/yellow]")
        return

    paths = [r.path for r in results]

    if new_name and len(paths) == 1:
        actions = [FileRenamer.prepare_single_rename(paths[0], new_name)]
    else:
        actions = FileRenamer.prepare_bulk_rename(
            items=paths,
            prefix=prefix,
            suffix=suffix,
            find_str=find_str,
            replace_str=replace_str,
            case_format=case,
            sequence_prefix=seq_prefix
        )

    # Render Preview Table
    PlanRenderer.render_preview(actions, dry_run=dry_run)

    if dry_run:
        console.print("[dim][Dry-Run Mode: No disk changes were executed.][/dim]")
        return

    # Check for valid actions to execute
    valid_actions = [a for a in actions if a.status == "OK"]
    if not valid_actions:
        console.print("[yellow]No valid actions to execute.[/yellow]")
        return

    if InteractiveUI.prompt_execution_confirmation(len(valid_actions)):
        successful, failed = FileRenamer.execute_rename_actions(valid_actions)
        if successful:
            session_id = logger.log_session(successful)
            console.print(f"[bold green]✓ Successfully renamed {len(successful)} item(s)![/bold green] (Undo ID: {session_id})")
        if failed:
            console.print(f"[bold red]✖ Failed to rename {len(failed)} item(s).[/bold red]")


@app.command("move")
def move_command(
    query: str = typer.Argument(..., help="Search query for files to move"),
    target_dir: str = typer.Argument(..., help="Destination directory path"),
    start_dir: str = typer.Option(".", "--start-dir", "-s", help="Directory to search in"),
    ext: Optional[List[str]] = typer.Option(None, "--ext", "-e", help="Extension filters"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Preview proposed actions without executing"),
):
    """
    🚚 Moves single or multiple files/folders to a target directory.
    """
    results = finder.search(query=query, start_dir=start_dir, extensions=ext)
    if not results:
        console.print(f"[yellow]No items found matching '{query}'.[/yellow]")
        return

    dest_path = Path(target_dir).resolve()
    sources = [r.path for r in results]

    actions = FileMover.prepare_move_actions(sources=sources, target_dir=dest_path)

    # Render Preview Table
    PlanRenderer.render_preview(actions, dry_run=dry_run)

    if dry_run:
        console.print("[dim][Dry-Run Mode: No disk changes were executed.][/dim]")
        return

    # Handle Missing Destination Directory Prompt
    requires_dest = any(a.requires_dest_creation for a in actions)
    if requires_dest and not dest_path.exists():
        user_agreed = InteractiveUI.prompt_create_destination(dest_path)
        if user_agreed:
            created = FileMover.create_destination_directory(dest_path, user_confirmed=True)
            if created:
                console.print(f"[bold green]✓ Destination directory created:[/bold green] {dest_path}")
                # Re-evaluate actions after creating directory
                actions = FileMover.prepare_move_actions(sources=sources, target_dir=dest_path)
            else:
                console.print("[bold red]Failed to create target directory. Aborting move.[/bold red]")
                return
        else:
            console.print("[yellow]Move cancelled: Target directory was not created.[/yellow]")
            return

    valid_actions = [a for a in actions if a.status == "OK"]
    if not valid_actions:
        console.print("[yellow]No valid actions to execute.[/yellow]")
        return

    if InteractiveUI.prompt_execution_confirmation(len(valid_actions)):
        successful, failed = FileMover.execute_move_actions(valid_actions)
        if successful:
            session_id = logger.log_session(successful)
            console.print(f"[bold green]✓ Successfully moved {len(successful)} item(s)![/bold green] (Undo ID: {session_id})")
        if failed:
            console.print(f"[bold red]✖ Failed to move {len(failed)} item(s).[/bold red]")


@app.command("ask")
def ask_command(
    prompt: str = typer.Argument(..., help="Natural language request (e.g. 'Move all PNGs from Desktop to Pictures')"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Preview proposed actions without executing"),
):
    """
    🤖 Natural language AI assistant powered by Local LLMs (Gemma/Qwen 4B) or Cloud Gemini.
    """
    console.print(f"[cyan]Parsing request with AI engine:[/cyan] '{prompt}'...")
    ai_parser = AIIntentParser()
    intent_data, provider_name = ai_parser.parse(prompt)

    if not intent_data:
        console.print(f"[bold red]AI Engine failed to parse request using provider: {provider_name}[/bold red]")
        return

    console.print(f"[bold green]✓ Intent Parsed using {provider_name}:[/bold green]")
    action = intent_data.get("action")
    query = intent_data.get("query", "*")
    source_dir = intent_data.get("source_dir") or "."
    target_dir = intent_data.get("target_dir")
    new_name = intent_data.get("new_name")
    filters = intent_data.get("filters") or {}

    exts = filters.get("extensions")

    if action == "locate":
        locate_command(query=query, start_dir=source_dir, ext=exts)
    elif action == "rename":
        if not new_name:
            console.print("[red]AI error: Missing target rename name.[/red]")
            return
        rename_command(query=query, new_name=new_name, start_dir=source_dir, dry_run=dry_run)
    elif action == "move":
        if not target_dir:
            console.print("[red]AI error: Missing target move directory.[/red]")
            return
        move_command(query=query, target_dir=target_dir, start_dir=source_dir, ext=exts, dry_run=dry_run)
    else:
        console.print(f"[yellow]Unknown action parsed by AI: {action}[/yellow]")


@app.command("undo")
def undo_command():
    """
    ↩️ Reverses the last move or rename transaction session.
    """
    last = logger.get_last_session()
    if not last:
        console.print("[yellow]No transaction history found to undo.[/yellow]")
        return

    console.print(f"[cyan]Undoing last session:[/cyan] {last['session_id']} ({len(last['records'])} actions)")
    reversed_count, errors = logger.undo_last_session()

    if reversed_count > 0:
        console.print(f"[bold green]✓ Successfully restored {reversed_count} file(s) to original state![/bold green]")
    if errors:
        for err in errors:
            console.print(f"[bold red]✖ {err}[/bold red]")


def main_launcher():
    """
    Fallback launcher: If no CLI subcommands are passed, opens the Interactive Menu.
    """
    if len(sys.argv) == 1:
        choice = InteractiveUI.show_interactive_menu()
        if choice == "1":
            q = typer.prompt("Enter search query")
            locate_command(query=q)
        elif choice == "2":
            q = typer.prompt("Enter search query for file to rename")
            n = typer.prompt("Enter new filename")
            rename_command(query=q, new_name=n)
        elif choice == "3":
            q = typer.prompt("Enter search query for file(s) to move")
            t = typer.prompt("Enter target destination directory")
            move_command(query=q, target_dir=t)
        elif choice == "4":
            p = typer.prompt("Enter your natural language prompt")
            ask_command(prompt=p)
        elif choice == "5":
            undo_command()
        elif choice == "6":
            console.print("[cyan]Goodbye![/cyan]")
    else:
        app()


if __name__ == "__main__":
    main_launcher()
