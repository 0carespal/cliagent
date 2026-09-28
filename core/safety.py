"""
Safety Subsystem for cliagent.
Provides preview rendering (Dry-Run table using rich) and transaction logging/undo capabilities.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Union, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from config import HISTORY_FILE_PATH
from core.renamer import RenameAction
from core.mover import MoveAction

console = Console()


class TransactionLogger:
    """
    Manages session transaction logs in JSON format for the undo functionality.
    """

    def __init__(self, log_path: Path = HISTORY_FILE_PATH):
        self.log_path = Path(log_path).resolve()

    def log_session(self, actions: List[Union[RenameAction, MoveAction]]) -> str:
        """
        Logs executed actions to the JSON history file.
        Returns the unique session_id.
        """
        if not actions:
            return ""

        # Ensure parent directory (~/.cliagent) exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        records = []
        for action in actions:
            if isinstance(action, RenameAction):
                records.append({
                    "action_type": "RENAME",
                    "original_source": str(action.source_path.resolve()),
                    "executed_target": str(action.target_path.resolve()),
                })
            elif isinstance(action, MoveAction):
                records.append({
                    "action_type": "MOVE",
                    "original_source": str(action.source_path.resolve()),
                    "executed_target": str(action.target_path.resolve()),
                })

        session_entry = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "records": records,
        }

        # Load existing history or start fresh list
        history = self._load_history()
        history.append(session_entry)

        # Write back to JSON file
        try:
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            console.print(f"[bold red]Warning: Failed to write transaction log: {e}[/bold red]")

        return session_id

    def get_last_session(self) -> Optional[Dict]:
        """
        Retrieves the most recent transaction session from the log.
        """
        history = self._load_history()
        return history[-1] if history else None

    def undo_last_session(self) -> Tuple[int, List[str]]:
        """
        Reverses the actions recorded in the last transaction session.
        Returns (reversed_count, error_messages).
        """
        last_session = self.get_last_session()
        if not last_session:
            return 0, ["No transaction history found to undo."]

        records = last_session.get("records", [])
        reversed_count = 0
        errors = []

        # Iterate in REVERSE order so dependent file moves roll back cleanly
        for record in reversed(records):
            action_type = record["action_type"]
            current_target = Path(record["executed_target"])
            original_source = Path(record["original_source"])

            if not current_target.exists():
                errors.append(f"Cannot undo: Target '{current_target.name}' no longer exists.")
                continue

            try:
                # Ensure parent of original source exists
                original_source.parent.mkdir(parents=True, exist_ok=True)
                
                # Reverse rename or move
                if action_type in ("RENAME", "MOVE"):
                    current_target.rename(original_source)
                    reversed_count += 1
            except Exception as e:
                errors.append(f"Failed to restore '{current_target.name}': {e}")

        # Remove undone session from history log
        if reversed_count > 0:
            history = self._load_history()
            if history:
                history.pop()  # Remove last entry
                with open(self.log_path, "w", encoding="utf-8") as f:
                    json.dump(history, f, indent=2)

        return reversed_count, errors

    def _load_history(self) -> List[Dict]:
        if not self.log_path.exists():
            return []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []


class PlanRenderer:
    """
    Renders clean, colorful preview tables and banners for dry-run and execution confirmation.
    """

    @staticmethod
    def render_preview(actions: List[Union[RenameAction, MoveAction]], dry_run: bool = False):
        """
        Prints a formatted Rich preview table of proposed file operations.
        """
        if not actions:
            console.print("[yellow]No operations proposed.[/yellow]")
            return

        mode_title = "🔍 DRY-RUN PREVIEW (No disk changes)" if dry_run else "📋 PROPOSED ACTIONS PREVIEW"
        border_style = "cyan" if dry_run else "green"

        table = Table(title=mode_title, border_style=border_style, header_style="bold magenta")
        table.add_column("Type", style="bold yellow", width=8)
        table.add_column("Source Path", style="dim", overflow="fold")
        table.add_column("Target Path", style="bold white", overflow="fold")
        table.add_column("Status / Warning", width=25)

        missing_dest_flag = False
        collisions_flag = False

        for action in actions:
            action_type = "RENAME" if isinstance(action, RenameAction) else "MOVE"
            source_str = str(action.source_path)
            target_str = str(action.target_path)

            # Format status with colors
            if action.status == "OK":
                status_formatted = "[bold green]✓ Ready[/bold green]"
            elif action.status == "MISSING_DESTINATION":
                status_formatted = "[bold yellow]⚠️ Folder Missing[/bold yellow]"
                missing_dest_flag = True
            elif action.status == "COLLISION":
                status_formatted = "[bold red]✖ Name Collision[/bold red]"
                collisions_flag = True
            elif action.status == "NO_CHANGE":
                status_formatted = "[dim]No Change[/dim]"
            else:
                status_formatted = f"[red]{action.status}[/red]"

            table.add_row(action_type, source_str, target_str, status_formatted)

        console.print(table)

        # Print warning banners if issues exist
        if missing_dest_flag:
            console.print(
                Panel(
                    "[bold yellow]⚠️ Target destination folder does not exist.[/bold yellow]\n"
                    "You will be prompted: [italic]Create folder? [y/N][/italic]. If declined, move will be cancelled.",
                    style="yellow",
                    title="Destination Notice"
                )
            )

        if collisions_flag:
            console.print(
                Panel(
                    "[bold red]✖ Target file collision detected.[/bold red]\n"
                    "Conflicting files will be skipped automatically to prevent overwriting.",
                    style="red",
                    title="Collision Warning"
                )
            )
