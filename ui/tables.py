"""
Rich Terminal Table Rendering Module for cliagent.
Renders search results, action tables, and summary listings cleanly.
"""
from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.finder import SearchResult

console = Console()


class TableRenderer:
    """
    Renders terminal outputs using Rich tables.
    """

    @staticmethod
    def render_search_results(results: List[SearchResult], query: str = ""):
        """
        Displays search results in a formatted Rich table.
        """
        if not results:
            console.print(Panel(f"[yellow]No files or folders matched search query:[/yellow] '{query}'", title="Search Results"))
            return

        table = Table(
            title=f"🔍 Search Results for '[bold cyan]{query}[/bold cyan]' ({len(results)} matches found)",
            header_style="bold magenta",
            border_style="dim"
        )
        table.add_column("Score", style="bold yellow", justify="right", width=7)
        table.add_column("Type", width=8)
        table.add_column("Name", style="bold white")
        table.add_column("Size", justify="right", width=10)
        table.add_column("Location / Parent Folder", style="dim", overflow="fold")

        for r in results:
            item_type = "[cyan]FOLDER[/cyan]" if r.is_dir else "[green]FILE[/green]"
            score_str = f"{r.match_score:.0f}%"
            
            # Format human readable size
            size_str = "-" if r.is_dir else TableRenderer._format_bytes(r.size_bytes)

            table.add_row(
                score_str,
                item_type,
                r.name,
                size_str,
                str(r.parent_dir)
            )

        console.print(table)

    @staticmethod
    def _format_bytes(size_bytes: int) -> str:
        """Converts raw bytes to human readable format (KB, MB, GB)."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
