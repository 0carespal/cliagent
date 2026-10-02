"""
Safety Subsystem for cliagent.
Provides preview rendering (Dry-Run table using rich) and transaction logging/undo capabilities.
"""
import json
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Union, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from config import HISTORY_FILE_PATH
from core.renamer import RenameAction
from core.mover import MoveAction


def _get_console() -> Console:
    """Returns the shared theme console if available, otherwise creates a default Console."""
    try:
        from ui.theme import AutobotTheme
        return AutobotTheme.get_console()
    except Exception:
        return Console()


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

        # Ensure parent directory (~/.autobot) exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        records = []
        for action in actions:
            src_p = Path(action.source_path)
            tgt_p = Path(action.target_path)
            src_resolved = str(src_p.parent.resolve() / src_p.name)
            tgt_resolved = str(tgt_p.parent.resolve() / tgt_p.name)
            if isinstance(action, RenameAction):
                records.append({
                    "action_type": "RENAME",
                    "original_source": src_resolved,
                    "executed_target": tgt_resolved,
                })
            elif isinstance(action, MoveAction):
                records.append({
                    "action_type": "MOVE",
                    "original_source": src_resolved,
                    "executed_target": tgt_resolved,
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
            _get_console().print(f"[bold red]Warning: Failed to write transaction log: {e}[/bold red]")

        return session_id

    def get_last_session(self) -> Optional[Dict]:
        """
        Retrieves the most recent transaction session from the log.
        """
        history = self._load_history()
        return history[-1] if history else None

    def get_history(self, limit: int = 10) -> List[Dict]:
        """
        Retrieves recent transaction sessions up to `limit`.
        """
        history = self._load_history()
        return history[-limit:] if history else []

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
        unreversed_records = []

        # Iterate in REVERSE order so dependent file moves roll back cleanly
        for record in reversed(records):
            action_type = record["action_type"]
            current_target = Path(record["executed_target"])
            original_source = Path(record["original_source"])

            if not current_target.exists():
                errors.append(f"Cannot undo: Target '{current_target.name}' no longer exists.")
                unreversed_records.insert(0, record)
                continue

            orig_name = original_source.name
            tgt_name = current_target.name
            is_case_only = (
                original_source.parent.resolve() == current_target.parent.resolve()
                and orig_name.lower() == tgt_name.lower()
                and orig_name != tgt_name
            )

            # Prevent overwriting an already existing file/folder at original_source
            if not is_case_only and original_source.exists():
                errors.append(f"Cannot undo: Original source location '{original_source}' already exists.")
                unreversed_records.insert(0, record)
                continue

            try:
                # Ensure parent of original source exists
                original_source.parent.mkdir(parents=True, exist_ok=True)
                
                # Reverse rename or move using shutil.move (cross-volume and drive safe)
                if action_type in ("RENAME", "MOVE"):
                    if is_case_only:
                        temp_path = current_target.with_name(f"{current_target.name}.__tmp_{uuid.uuid4().hex[:8]}")
                        shutil.move(str(current_target), str(temp_path))
                        shutil.move(str(temp_path), str(original_source))
                    else:
                        shutil.move(str(current_target), str(original_source))
                    reversed_count += 1
            except Exception as e:
                errors.append(f"Failed to restore '{current_target.name}': {e}")
                unreversed_records.insert(0, record)

        # Update history log: pop if completely reversed or dead, or retain unreversed records if partial
        history = self._load_history()
        if history:
            all_dead = (reversed_count == 0 and len(errors) == len(records) and len(records) > 0)
            if reversed_count == len(records) or all_dead:
                history.pop()  # Completely reversed or un-restorable dead session
                if all_dead:
                    errors.append("All target items were missing or unrestorable. Discarded dead session from undo stack.")
            elif reversed_count > 0:
                # Partially reversed: update last session with only remaining un-reversed records
                history[-1]["records"] = unreversed_records

            try:
                with open(self.log_path, "w", encoding="utf-8") as f:
                    json.dump(history, f, indent=2)
            except Exception as e:
                errors.append(f"Failed to update transaction log: {e}")

        return reversed_count, errors

    def _load_history(self) -> List[Dict]:
        if not self.log_path.exists():
            return []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
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
        con = _get_console()
        if not actions:
            con.print("[yellow]No operations proposed.[/yellow]")
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
        invalid_flag = False

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
            elif action.status in ("INVALID_MOVE", "INVALID_NAME"):
                status_formatted = f"[bold red]✖ {action.status}[/bold red]"
                invalid_flag = True
            elif action.status == "NO_CHANGE":
                status_formatted = "[dim]No Change[/dim]"
            else:
                status_formatted = f"[red]{action.status}[/red]"

            table.add_row(action_type, source_str, target_str, status_formatted)

        con.print(table)

        # Print warning banners if issues exist
        if missing_dest_flag:
            con.print(
                Panel(
                    "[bold yellow]⚠️ Target destination folder does not exist.[/bold yellow]\n"
                    "You will be prompted: [italic]Create folder? [y/N][/italic]. If declined, move will be cancelled.",
                    style="yellow",
                    title="Destination Notice"
                )
            )

        if collisions_flag:
            con.print(
                Panel(
                    "[bold red]✖ Target file collision detected.[/bold red]\n"
                    "Conflicting files will be skipped automatically to prevent overwriting.",
                    style="red",
                    title="Collision Warning"
                )
            )

        if invalid_flag:
            con.print(
                Panel(
                    "[bold red]✖ Invalid operation detected.[/bold red]\n"
                    "Operations that violate safety constraints (e.g. moving a folder into itself) will be aborted.",
                    style="red",
                    title="Safety Warning"
                )
            )
