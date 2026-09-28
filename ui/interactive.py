"""
Interactive Prompts and Fallback Menu Module for cliagent.
Handles missing folder creation prompts and interactive menu selections.
"""
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm, Prompt

console = Console()


class InteractiveUI:
    """
    Provides interactive terminal user input prompts.
    """

    @staticmethod
    def prompt_create_destination(target_dir: Path) -> bool:
        """
        Prompts the user whether to create a missing destination folder.
        Creates folder ONLY if user responds with 'y' or 'Y'.
        """
        console.print(
            f"\n[bold yellow]⚠️  Notice:[/bold yellow] Destination directory does not exist:\n"
            f"   [cyan]{target_dir.resolve()}[/cyan]"
        )
        # Confirm returns True ONLY if user types y or Y (default is False)
        return Confirm.ask("Do you want to create this directory?", default=False)

    @staticmethod
    def prompt_execution_confirmation(action_count: int) -> bool:
        """
        Asks user to confirm execution of proposed file actions.
        """
        return Confirm.ask(f"Execute these {action_count} proposed actions?", default=True)

    @staticmethod
    def show_interactive_menu() -> str:
        """
        Displays an interactive main menu when cliagent is launched without flags.
        """
        console.print("\n[bold cyan]===============================================[/bold cyan]")
        console.print("[bold cyan]       🤖 cliagent — Interactive Menu         [/bold cyan]")
        console.print("[bold cyan]===============================================[/bold cyan]")
        console.print("  [bold yellow]1.[/bold yellow] 🔍 Locate Files / Folders")
        console.print("  [bold yellow]2.[/bold yellow] ✏️  Rename Files / Folders")
        console.print("  [bold yellow]3.[/bold yellow] 🚚 Move Files / Folders")
        console.print("  [bold yellow]4.[/bold yellow] 🤖 Ask AI Assistant (Natural Language)")
        console.print("  [bold yellow]5.[/bold yellow] ↩️  Undo Last Session")
        console.print("  [bold yellow]6.[/bold yellow] ❌ Exit\n")

        choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5", "6"], default="1")
        return choice
