"""
Interactive Prompts, Selection Cards, and Confirmation Guardrails for Autobot CLI.
Provides rich interactive confirmation menus (powered by InquirerPy with Rich fallbacks)
for action execution, missing directory creation, and transaction undo reversals.
"""

import sys
from pathlib import Path
from typing import List, Union, Optional
from rich.prompt import Confirm, Prompt

from ui.theme import AutobotTheme
from core.renamer import RenameAction
from core.mover import MoveAction
from core.safety import PlanRenderer

try:
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice
    INQUIRER_AVAILABLE = True
except ImportError:
    INQUIRER_AVAILABLE = False


class InteractiveUI:
    """
    Interactive terminal user input prompts and safety confirmation dialogs.
    """

    @staticmethod
    def prompt_create_destination(target_dir: Path, yes: bool = False) -> bool:
        """
        Prompts user whether to create a missing destination folder.
        Creates folder ONLY if user responds affirmatively (y/Y).
        """
        if yes:
            return True

        AutobotTheme.get_console().print(
            f"\n[bold yellow]⚠️  Notice:[/bold yellow] Target destination directory does not exist:\n"
            f"   📁 [dim cyan]{target_dir.resolve()}[/dim cyan]\n"
        )
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            return False

        if INQUIRER_AVAILABLE:
            try:
                result = inquirer.confirm(
                    message=f"Create missing directory '{target_dir.name}'?",
                    default=False
                ).execute()
                return result
            except Exception:
                pass
        return Confirm.ask("Do you want to create this directory?", default=False)

    @staticmethod
    def confirm_action_execution(
        actions: List[Union[RenameAction, MoveAction]],
        dry_run: bool = False,
        yes: bool = False
    ) -> bool:
        """
        Displays framed preview table of proposed actions and requires user confirmation.
        Returns True if confirmed for execution, False if cancelled or dry-run.
        """
        if not actions:
            AutobotTheme.render_warning("No valid operations proposed.")
            return False

        # First render framed preview table card
        PlanRenderer.render_preview(actions, dry_run=dry_run)

        if dry_run:
            AutobotTheme.render_warning("Dry-run preview complete. No files were modified on disk.")
            return False

        # Interactive confirmation guardrail
        valid_actions = [a for a in actions if a.status in ("OK", "MISSING_DESTINATION")]
        if not valid_actions:
            AutobotTheme.render_error("No valid actions to execute due to file collisions or missing paths.")
            return False

        if yes:
            return True

        if not sys.stdin.isatty() or not sys.stdout.isatty():
            return True

        if INQUIRER_AVAILABLE:
            try:
                choice = inquirer.select(
                    message=f"Proposed {len(valid_actions)} file operation(s): Select action",
                    choices=[
                        Choice(value="execute", name="✓ Execute actions now"),
                        Choice(value="cancel", name="✖ Cancel operation")
                    ],
                    default="execute"
                ).execute()
                return choice == "execute"
            except Exception:
                pass

        return Confirm.ask(f"Execute these {len(valid_actions)} proposed actions?", default=True)

    @staticmethod
    def prompt_undo_confirmation(session_id: str, action_count: int, yes: bool = False) -> bool:
        """
        Asks user to confirm reversing a transaction history session.
        """
        if yes:
            return True

        AutobotTheme.get_console().print(
            f"\n[bold yellow]↩️  Undo Request:[/bold yellow] Reverse session [bold cyan]{session_id}[/bold cyan] ({action_count} file actions)"
        )
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            return True

        if INQUIRER_AVAILABLE:
            try:
                return inquirer.confirm(
                    message=f"Reverse {action_count} file actions from last session?",
                    default=True
                ).execute()
            except Exception:
                pass
        return Confirm.ask("Proceed with reversing these file operations?", default=True)
