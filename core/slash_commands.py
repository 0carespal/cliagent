"""
Slash Command Router and Handlers for Autobot CLI.
Parses slash command inputs (/locate, /rename, /move, /undo, /model, /status, /help, /clear, /exit)
and dispatches them directly to core file engines and UI theme renderers.
"""

import shlex
import sys
from pathlib import Path
from typing import List, Optional, Any

import config
from ui.theme import AutobotTheme
from ui.tables import TableRenderer
from ui.interactive import InteractiveUI
from core.finder import FileFinder
from core.renamer import FileRenamer
from core.mover import FileMover
from core.safety import TransactionLogger, PlanRenderer


class SlashCommandRouter:
    """
    Parses and dispatches slash commands executed inside the Autobot REPL.
    """

    def __init__(self):
        self.finder = FileFinder()
        self.renamer = FileRenamer()
        self.mover = FileMover()
        self.logger = TransactionLogger()

    def is_slash_command(self, user_input: str) -> bool:
        """Checks if input string starts with slash '/'."""
        return user_input.strip().startswith("/")

    def dispatch(self, user_input: str, repl_instance: Any) -> bool:
        """
        Dispatches slash command input.
        Returns True if handled as a slash command, False if raw natural language input.
        """
        trimmed = user_input.strip()
        if not trimmed.startswith("/"):
            return False

        try:
            tokens = shlex.split(trimmed)
        except Exception:
            tokens = trimmed.split()

        cmd = tokens[0].lower()
        args = tokens[1:]

        if cmd == "/locate":
            self.handle_locate(args, repl_instance)
        elif cmd == "/rename":
            self.handle_rename(args, repl_instance)
        elif cmd == "/move":
            self.handle_move(args, repl_instance)
        elif cmd == "/undo":
            self.handle_undo(repl_instance)
        elif cmd == "/key":
            self.handle_key(args, repl_instance)
        elif cmd in ["/model", "/models"]:
            model_args = ["list"] if (cmd == "/models" and not args) else args
            self.handle_model(model_args, repl_instance)
        elif cmd == "/status":
            self.handle_status(repl_instance)
        elif cmd in ["/help", "/h", "/?"]:
            self.handle_help(repl_instance)
        elif cmd in ["/clear", "/cls"]:
            # Handled in REPL loop
            pass
        elif cmd in ["/exit", "/quit"]:
            # Handled in REPL loop
            pass
        else:
            AutobotTheme.render_warning(f"Unknown slash command '[bold]{cmd}[/bold]'. Type [bold cyan]/help[/bold cyan] for available commands.")

        return True

    def handle_locate(self, args: List[str], repl_instance: Any) -> None:
        """
        🔍 Handles /locate <query> [--start-dir DIR] [--ext EXT1 EXT2]
        """
        if not args:
            AutobotTheme.render_warning("Missing search query. Usage: [bold cyan]/locate <query> [--start-dir DIR] [--ext pdf png][/bold cyan]")
            return

        query = args[0]
        start_dir = str(repl_instance.cwd)
        exts = None

        # Parse simple options if provided
        idx = 1
        while idx < len(args):
            arg = args[idx]
            if arg in ["--start-dir", "-s"] and idx + 1 < len(args):
                start_dir = args[idx + 1]
                idx += 2
            elif arg in ["--ext", "-e"] and idx + 1 < len(args):
                exts = args[idx + 1:]
                break
            else:
                idx += 1

        AutobotTheme.get_console().print(f"[dim cyan]Searching for:[/dim cyan] '{query}' in [bold]{start_dir}[/bold]...")
        try:
            with AutobotTheme.status(f"Searching directory tree for '{query}'..."):
                results = self.finder.search(query=query, start_dir=start_dir, extensions=exts)
            TableRenderer.render_search_results(results, query=query)
        except Exception as e:
            AutobotTheme.render_error(f"Search failed: {e}")

    def handle_rename(self, args: List[str], repl_instance: Any) -> None:
        """
        ✏️ Handles /rename <query> <new_name>
        """
        if len(args) < 2:
            AutobotTheme.render_warning("Usage: [bold cyan]/rename <search_query> <new_name>[/bold cyan]")
            return

        query = args[0]
        new_name = args[1]

        try:
            with AutobotTheme.status(f"Preparing rename for '{query}' -> '{new_name}'..."):
                actions = self.renamer.prepare_single_rename(
                    query=query,
                    new_name=new_name,
                    start_dir=str(repl_instance.cwd)
                )
            if not actions:
                AutobotTheme.render_warning(f"No file matching query '{query}' was found to rename.")
                return

            # Interactive confirmation guardrail
            if not InteractiveUI.confirm_action_execution(actions, dry_run=False):
                AutobotTheme.render_warning("Rename operation cancelled by user.")
                return

            # Execute rename actions
            with AutobotTheme.status("Executing file rename operation..."):
                executed, errors = self.renamer.execute_rename(actions)
            if executed:
                session_id = self.logger.log_session(executed)
                AutobotTheme.render_success(f"Renamed {len(executed)} item(s) successfully! Logged in transaction session [dim]{session_id}[/dim]")
            if errors:
                for err in errors:
                    AutobotTheme.render_error(err)
        except Exception as e:
            AutobotTheme.render_error(f"Rename action failed: {e}")

    def handle_move(self, args: List[str], repl_instance: Any) -> None:
        """
        🚚 Handles /move <query> <target_dir>
        """
        if len(args) < 2:
            AutobotTheme.render_warning("Usage: [bold cyan]/move <search_query> <target_directory>[/bold cyan]")
            return

        query = args[0]
        target_dir = args[1]

        try:
            with AutobotTheme.status(f"Preparing relocation for '{query}' -> '{target_dir}'..."):
                actions = self.mover.prepare_move(
                    query=query,
                    target_dir=target_dir,
                    start_dir=str(repl_instance.cwd)
                )
            if not actions:
                AutobotTheme.render_warning(f"No files/folders matching '{query}' found to move.")
                return

            # Check if destination directory is missing
            missing_dest = any(a.requires_dest_creation or a.status == "MISSING_DESTINATION" for a in actions)
            if missing_dest:
                target_path = Path(target_dir) if Path(target_dir).is_absolute() else (repl_instance.cwd / target_dir)
                if not target_path.exists():
                    if InteractiveUI.prompt_create_destination(target_path):
                        self.mover.create_destination_directory(target_path, user_confirmed=True)
                        for a in actions:
                            if a.status == "MISSING_DESTINATION":
                                a.status = "OK"
                                a.message = "Destination created. Ready to move."
                    else:
                        AutobotTheme.render_warning("Destination creation cancelled. Move operation aborted.")
                        return

            # Interactive confirmation guardrail
            if not InteractiveUI.confirm_action_execution(actions, dry_run=False):
                AutobotTheme.render_warning("Move operation cancelled by user.")
                return

            # Execute move actions
            with AutobotTheme.status("Executing file move operation..."):
                executed, errors = self.mover.execute_move(actions)
            if executed:
                session_id = self.logger.log_session(executed)
                AutobotTheme.render_success(f"Moved {len(executed)} item(s) to '{target_dir}'! Transaction session: [dim]{session_id}[/dim]")
            if errors:
                for err in errors:
                    AutobotTheme.render_error(err)
        except Exception as e:
            AutobotTheme.render_error(f"Move action failed: {e}")

    def handle_undo(self, repl_instance: Any) -> None:
        """
        ↩️ Handles /undo
        Reverses the last recorded move or rename session.
        """
        last_session = self.logger.get_last_session()
        if not last_session:
            AutobotTheme.render_warning("No transaction history found to undo.")
            return

        session_id = last_session.get("session_id", "unknown")
        records_count = len(last_session.get("records", []))

        # Interactive undo confirmation
        if not InteractiveUI.prompt_undo_confirmation(session_id, records_count):
            AutobotTheme.render_warning("Undo operation cancelled by user.")
            return

        AutobotTheme.get_console().print(f"[cyan]Undoing session:[/cyan] [bold]{session_id}[/bold] ({records_count} action(s))...")
        reversed_count, errors = self.logger.undo_last_session()

        if reversed_count > 0:
            AutobotTheme.render_success(f"Successfully restored {reversed_count} file(s) to original location and state!")
        if errors:
            for err in errors:
                AutobotTheme.render_error(err)

    def handle_key(self, args: List[str], repl_instance: Any) -> None:
        """
        🔑 Handles /key [api_key]
        Views or sets Cloud LLM API key.
        """
        if not args:
            cfg = config.load_user_config()
            current_key = config.LLM_API_KEY or cfg.get("llm_api_key", "")
            if current_key:
                masked = current_key[:3] + "..." + current_key[-4:] if len(current_key) > 7 else "***"
                AutobotTheme.render_card(
                    title="🔑 Cloud LLM API Key Status",
                    content=f"API Key is configured: [bold green]{masked}[/bold green]\nTarget Model: [bold yellow]{config.LLM_MODEL}[/bold yellow]\nEndpoint: [dim]{config.LLM_BASE_URL}[/dim]",
                    style="green"
                )
            else:
                AutobotTheme.render_warning(
                    "No Cloud LLM API key configured.\n"
                    "Set one via: [bold cyan]/key <YOUR_API_KEY>[/bold cyan] or export [bold]LLM_API_KEY[/bold] in your environment."
                )
            return

        new_key = args[0].strip()
        config.save_user_config("llm_api_key", new_key)
        config.LLM_API_KEY = new_key

        # If previously no model was available, switch active session model to Cloud LLM
        if hasattr(repl_instance, "model_name") and repl_instance.model_name == "No model available":
            repl_instance.set_model(f"Cloud LLM ({config.LLM_MODEL})")

        masked = new_key[:3] + "..." + new_key[-4:] if len(new_key) > 7 else "***"
        AutobotTheme.render_card(
            title="🔑 API Key Configured",
            content=f"Saved Cloud LLM API key: [bold green]{masked}[/bold green]\nTarget Model: [bold yellow]{config.LLM_MODEL}[/bold yellow]\nPersisted to: [dim]~/.autobot/config.json[/dim]",
            style="green"
        )

    def handle_model(self, args: List[str], repl_instance: Any) -> None:
        """
        🧠 Handles /model [list|local|cloud|model_name]
        Toggles, lists, or switches active LLM model provider.
        """
        from ai.local_llm import LocalLLMClient
        from ai.cloud_llm import CloudLLMClient

        local_client = LocalLLMClient()
        cloud_client = CloudLLMClient()
        cfg = config.load_user_config()
        cloud_model_name = config.LLM_MODEL or cfg.get("llm_model", "gpt-4o-mini")
        cloud_label = f"Cloud LLM ({cloud_model_name})"

        # 1. /model list or /models
        if args and args[0].lower() in ["list", "ls", "--list", "-l"]:
            installed_local = local_client.list_installed_models()
            lines = []
            
            lines.append("[bold cyan]Local Models (Ollama at http://localhost:11434):[/bold cyan]")
            if installed_local:
                for m in installed_local:
                    active_marker = " [bold green]✓ Active[/bold green]" if m in repl_instance.model_name else ""
                    lines.append(f"  • [bold white]{m}[/bold white]{active_marker}")
            else:
                lines.append("  [dim]• No local models detected (ensure Ollama is running)[/dim]")

            lines.append("\n[bold cyan]Cloud LLM (Universal OpenAI-compatible):[/bold cyan]")
            key_status = "[bold green]Configured[/bold green]" if cloud_client.is_available() else "[dim yellow]No API Key (use /key)[/dim yellow]"
            cloud_active = " [bold green]✓ Active[/bold green]" if "Cloud" in repl_instance.model_name else ""
            lines.append(f"  • [bold white]{cloud_model_name}[/bold white] ({key_status}){cloud_active}")

            lines.append(f"\n[bold white]Current Active Session Model:[/bold white] [bold yellow]{repl_instance.model_name}[/bold yellow]")

            AutobotTheme.render_card(
                title="🧠 Available LLM Models",
                content="\n".join(lines),
                style="cyan",
                subtitle="Switch model with: /model <name> or /model cloud"
            )
            return

        installed_local = local_client.list_installed_models()
        best_local_name = local_client.resolve_model_name() if installed_local else "qwen2.5:4b"
        local_label = f"Local LLM ({best_local_name})"

        # 2. /model (no args -> toggle)
        if not args:
            current = repl_instance.model_name
            if current == "No model available":
                if cloud_client.is_available():
                    new_model = cloud_label
                elif installed_local:
                    new_model = local_label
                else:
                    AutobotTheme.render_warning("No model available. Set a key via: /key <API_KEY> or run /model list.")
                    return
            else:
                new_model = cloud_label if "Local" in current else local_label

            repl_instance.set_model(new_model)
            if "Local" in new_model:
                config.save_user_config("local_llm_model", best_local_name)
            AutobotTheme.render_success(f"Switched LLM Provider model to: [bold yellow]{new_model}[/bold yellow]")
            return

        choice = args[0]
        choice_lower = choice.lower()

        # 3. Switch to Cloud
        if choice_lower in ["cloud", "openai", "remote", "api"]:
            repl_instance.set_model(cloud_label)
            AutobotTheme.render_success(f"Switched LLM Provider to: [bold yellow]{cloud_label}[/bold yellow]")
            if not cloud_client.is_available():
                AutobotTheme.render_warning("⚠️ Note: Cloud LLM API key not configured yet. Run: [bold cyan]/key <YOUR_API_KEY>[/bold cyan]")
            return

        # 4. Switch to Local
        if choice_lower in ["local", "ollama"]:
            if not installed_local:
                AutobotTheme.render_warning("No local models found in Ollama. Pull one with e.g. [bold cyan]ollama run qwen3.5:4b[/bold cyan]")
                return
            model_name = local_label
            config.save_user_config("local_llm_model", best_local_name)
            repl_instance.set_model(model_name)
            AutobotTheme.render_success(f"Switched to Local LLM model: [bold yellow]{model_name}[/bold yellow]")
            return

        # 5. Check if choice matches any installed local model
        matched_local = None
        for m in installed_local:
            if m.lower() == choice_lower:
                matched_local = m
                break
        if not matched_local:
            for m in installed_local:
                if choice_lower in m.lower():
                    matched_local = m
                    break

        if matched_local:
            model_name = f"Local LLM ({matched_local})"
            config.save_user_config("local_llm_model", matched_local)
        else:
            model_name = choice

        repl_instance.set_model(model_name)
        AutobotTheme.render_success(f"Updated LLM Provider model to: [bold yellow]{model_name}[/bold yellow]")

    def handle_status(self, repl_instance: Any) -> None:
        """
        📊 Handles /status
        Displays a summary card of current REPL session metrics.
        """
        undo_count = repl_instance.get_undo_count()
        content = (
            f"📁 [bold white]Active Folder:[/bold white] [dim cyan]{repl_instance.cwd.resolve()}[/dim cyan]\n"
            f"🧠 [bold white]LLM Model:[/bold white] [bold yellow]{repl_instance.model_name}[/bold yellow]\n"
            f"↩️ [bold white]Undo Stack:[/bold white] [green]{undo_count} session(s) logged[/green]\n"
            f"💻 [bold white]Python Environment:[/bold white] [dim]{sys.version.split()[0]}[/dim]"
        )
        AutobotTheme.render_card(
            title="📊 Autobot Session Status",
            content=content,
            style="cyan",
            subtitle="Type /help for slash command documentation"
        )

    def handle_help(self, repl_instance: Any) -> None:
        """
        💡 Handles /help
        Renders slash command cheat-sheet card.
        """
        help_text = (
            "[bold cyan]/locate <query> [--ext ...][/bold cyan]     🔍 Locate files matching query using fuzzy search\n"
            "[bold cyan]/rename <query> <new_name>[/bold cyan]      ✏️  Rename matching file/folder\n"
            "[bold cyan]/move <query> <target_dir>[/bold cyan]      🚚 Move matching files to target folder\n"
            "[bold cyan]/undo[/bold cyan]                            ↩️  Reverse last move/rename transaction\n"
            "[bold cyan]/key [api_key][/bold cyan]                   🔑 View or configure Cloud LLM API key\n"
            "[bold cyan]/model [list|local|cloud][/bold cyan]     🧠 View models (/model list) or switch active LLM\n"
            "[bold cyan]/status[/bold cyan]                          📊 View current active folder, model, & undo stack\n"
            "[bold cyan]/clear[/bold cyan]                           🧹 Clear terminal screen canvas\n"
            "[bold cyan]/exit[/bold cyan]                            ❌ Exit Autobot REPL session\n\n"
            "[dim white]💡 Pro Tip: Type any plain English prompt without a slash to use natural language AI processing![/dim white]"
        )
        AutobotTheme.render_card(
            title="💡 Autobot Command Cheat-Sheet",
            content=help_text,
            style="magenta"
        )
