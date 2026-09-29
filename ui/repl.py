"""
Persistent REPL Shell Loop Engine for Autobot CLI.
Provides a live, continuous terminal session with tab auto-completion,
command history, signal handling, and session state tracking.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Callable
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import Completer, Completion, PathCompleter, WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.output import DummyOutput

from ui.theme import AutobotTheme
from core.safety import TransactionLogger


class AutobotCompleter(Completer):
    """
    Combined Completer for Autobot REPL:
    Auto-completes slash commands (/locate, /rename, /move, /undo, /model, /status, /help, /clear, /exit)
    as well as local file system paths.
    """

    SLASH_COMMANDS = [
        "/locate",
        "/rename",
        "/move",
        "/undo",
        "/model",
        "/status",
        "/help",
        "/clear",
        "/exit"
    ]

    def __init__(self, get_cwd: Callable[[], Path]):
        self.get_cwd = get_cwd
        self.word_completer = WordCompleter(self.SLASH_COMMANDS, ignore_case=True)
        self.path_completer = PathCompleter(expanduser=True)

    def get_completions(self, document, complete_event):
        text_before_cursor = document.text_before_cursor

        # If user is typing a slash command at the start of the line
        if text_before_cursor.startswith("/"):
            for completion in self.word_completer.get_completions(document, complete_event):
                yield completion
        else:
            # Complete file paths
            for completion in self.path_completer.get_completions(document, complete_event):
                yield completion


class AutobotREPL:
    """
    Interactive REPL session manager maintaining session state, prompt history,
    and handling input signals.
    """

    def __init__(
        self,
        handler_callback: Optional[Callable[[str, "AutobotREPL"], None]] = None,
        model_name: str = "Gemma 4B (Local)"
    ):
        self.handler_callback = handler_callback
        self.cwd = Path.cwd()
        self.model_name = model_name
        self.logger = TransactionLogger()
        
        # Setup history directory ~/.autobot/
        self.history_dir = Path.home() / ".autobot"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        history_file = self.history_dir / "repl_history.txt"

        self.completer = AutobotCompleter(get_cwd=lambda: self.cwd)

        # Handle non-TTY pipe environments gracefully
        try:
            if not sys.stdout.isatty():
                self.session = PromptSession(
                    history=FileHistory(str(history_file)),
                    completer=self.completer,
                    output=DummyOutput()
                )
            else:
                self.session = PromptSession(
                    history=FileHistory(str(history_file)),
                    completer=self.completer
                )
        except Exception:
            # Fallback to DummyOutput if console screen buffer is not available
            self.session = PromptSession(
                history=FileHistory(str(history_file)),
                completer=self.completer,
                output=DummyOutput()
            )

    def get_undo_count(self) -> int:
        """Returns the number of recorded transaction sessions available for undo."""
        history = self.logger._load_history()
        return len(history)

    def set_model(self, model_name: str) -> None:
        """Updates the active model name for the session."""
        self.model_name = model_name

    def prompt_input(self, prompt_text: str = "autobot › ") -> str:
        """Reads a single line of input using prompt_toolkit or fallback."""
        try:
            prompt_html = HTML("<bold><magenta>autobot</magenta> <cyan>›</cyan> </bold>")
            return self.session.prompt(prompt_html).strip()
        except Exception:
            return input(prompt_text).strip()

    def run(self) -> None:
        """
        Starts the continuous REPL session loop.
        """
        # Render Option A startup banner
        AutobotTheme.render_banner(
            version="1.0.0",
            model_name=self.model_name,
            cwd=self.cwd,
            undo_count=self.get_undo_count()
        )

        while True:
            try:
                # Prompt user for input
                user_input = self.prompt_input()

                if not user_input:
                    continue

                if user_input.lower() in ["/exit", "exit", "quit", ":q"]:
                    AutobotTheme.get_console().print("[bold cyan]Goodbye! Exiting Autobot session.[/bold cyan]")
                    break

                if user_input.lower() == "/clear":
                    os.system("cls" if os.name == "nt" else "clear")
                    continue

                # Pass user input to registered handler callback
                if self.handler_callback:
                    self.handler_callback(user_input, self)
                else:
                    AutobotTheme.get_console().print(f"[dim]Echo: {user_input}[/dim]")

            except KeyboardInterrupt:
                # Ctrl+C clears line without terminating session
                AutobotTheme.get_console().print("\n[dim yellow](Use /exit or Ctrl+D to exit session)[/dim yellow]")
                continue
            except EOFError:
                # Ctrl+D exits session
                AutobotTheme.get_console().print("\n[bold cyan]Goodbye! Exiting Autobot session.[/bold cyan]")
                break
            except Exception as e:
                AutobotTheme.render_error(f"Unexpected REPL error: {e}")
