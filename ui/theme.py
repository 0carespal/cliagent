"""
Centralized Theme and Styling Engine for Autobot CLI.
Provides unified color palettes, Rich styles, header banners, status bars, and UI cards.
Inspired by Antigravity CLI and modern developer terminal tools.
"""

import sys
import io
from pathlib import Path
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

# Ensure UTF-8 output encoding for Windows command line streams
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Custom Rich Theme palette definition matching Antigravity CLI aesthetics
AUTOBOT_THEME = Theme({
    "brand": "bold magenta",
    "accent": "bold cyan",
    "muted": "dim white",
    "dim_path": "dim cyan",
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
    "badge_bg": "bold white on blue",
    "badge_local": "bold white on dark_magenta",
    "badge_cloud": "bold white on dark_cyan",
    "border": "cyan",
    "table_header": "bold cyan",
})


class AutobotTheme:
    """
    Central Manager for all terminal formatting, banners, status bars, and cards.
    """

    console = Console(theme=AUTOBOT_THEME)

    @classmethod
    def get_console(cls) -> Console:
        """Returns the shared Rich Console instance."""
        return cls.console

    @classmethod
    def render_banner(
        cls,
        version: str = "1.0.0",
        model_name: str = "Gemma 4B (Local)",
        cwd: Optional[Path] = None,
        undo_count: int = 0
    ) -> None:
        """
        Renders Option A — Full ASCII / Box Banner with rounded borders,
        live status metrics, and helpful slash command tips.
        """
        cwd_path = str((cwd or Path.cwd()).resolve())
        
        banner_text = Text()
        banner_text.append("🤖 AUTOBOT ", style="bold magenta")
        banner_text.append(f"v{version}", style="dim white")
        banner_text.append(" — Intelligent File & Folder Management Agent\n", style="bold cyan")
        
        banner_text.append("\n  📁 Directory: ", style="bold white")
        banner_text.append(f"{cwd_path}", style="dim cyan")
        
        banner_text.append("\n  🧠 LLM Model: ", style="bold white")
        banner_text.append(f"[{model_name}]", style="bold yellow")
        
        banner_text.append("\n  ↩️ Undo Stack: ", style="bold white")
        banner_text.append(f"{undo_count} session(s) logged", style="green" if undo_count > 0 else "dim white")

        banner_text.append("\n\n  💡 Quick Commands: ", style="bold white")
        banner_text.append("/locate", style="bold cyan")
        banner_text.append(" • ", style="dim white")
        banner_text.append("/rename", style="bold cyan")
        banner_text.append(" • ", style="dim white")
        banner_text.append("/move", style="bold cyan")
        banner_text.append(" • ", style="dim white")
        banner_text.append("/undo", style="bold cyan")
        banner_text.append(" • ", style="dim white")
        banner_text.append("/model", style="bold cyan")
        banner_text.append(" • ", style="dim white")
        banner_text.append("/help", style="bold cyan")

        panel = Panel(
            banner_text,
            title="[bold magenta]Antigravity CLI Workspace[/bold magenta]",
            subtitle="[dim white]Type natural language or /help for slash commands[/dim white]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        cls.console.print(panel)

    @classmethod
    def render_status_bar(
        cls,
        cwd: Path,
        model_name: str,
        undo_count: int
    ) -> None:
        """
        Renders a compact 1-line status bar at the top of REPL steps.
        """
        table = Table.grid(expand=True)
        table.add_column(justify="left", ratio=3)
        table.add_column(justify="center", ratio=2)
        table.add_column(justify="right", ratio=2)

        dir_str = f"📁 [dim cyan]{cwd.resolve()}[/dim cyan]"
        model_str = f"🧠 [bold yellow]{model_name}[/bold yellow]"
        undo_str = f"↩️ [green]{undo_count} session(s)[/green]" if undo_count > 0 else "↩️ [dim]0 sessions[/dim]"

        table.add_row(dir_str, model_str, undo_str)
        cls.console.print(Panel(table, box=box.HORIZONTALS, border_style="dim cyan"))

    @classmethod
    def get_prompt_symbol(cls) -> str:
        """
        Returns the formatted REPL prompt symbol.
        """
        return "[bold magenta]autobot[/bold magenta] [bold cyan]›[/bold cyan] "

    @classmethod
    def render_card(
        cls,
        title: str,
        content: str,
        style: str = "cyan",
        subtitle: Optional[str] = None
    ) -> None:
        """
        Renders content inside a framed rounded Panel card.
        """
        panel = Panel(
            content,
            title=f"[bold]{title}[/bold]",
            subtitle=f"[dim]{subtitle}[/dim]" if subtitle else None,
            border_style=style,
            box=box.ROUNDED,
            padding=(0, 1)
        )
        cls.console.print(panel)

    @classmethod
    def render_error(cls, message: str) -> None:
        """Renders error messages with consistent styling."""
        cls.console.print(f"[bold red]✖ Error:[/bold red] {message}")

    @classmethod
    def render_success(cls, message: str) -> None:
        """Renders success messages with consistent styling."""
        cls.console.print(f"[bold green]✓ Success:[/bold green] {message}")

    @classmethod
    def render_warning(cls, message: str) -> None:
        """Renders warning messages with consistent styling."""
        cls.console.print(f"[bold yellow]⚠️ Warning:[/bold yellow] {message}")

    @classmethod
    def status(cls, message: str, spinner: str = "dots"):
        """
        Context manager for rendering live animated progress spinners.
        Usage:
            with AutobotTheme.status("Searching directory tree..."):
                results = finder.search(...)
        """
        return cls.console.status(f"[bold cyan]{message}[/bold cyan]", spinner=spinner)

