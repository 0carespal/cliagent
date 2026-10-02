"""
End-to-End Automated Test Suite for Autobot CLI Agent.
Validates Finder, Renamer, Mover, Safety undo log, Theme, REPL session, and Slash Command Router.
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from core.finder import FileFinder
from core.renamer import FileRenamer
from core.mover import FileMover
from core.safety import TransactionLogger, PlanRenderer
from core.slash_commands import SlashCommandRouter
from ui.theme import AutobotTheme
from ui.repl import AutobotREPL


class TestAutobotCLI(unittest.TestCase):
    """
    Integration tests covering core engines, slash router, and safety subsystem.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_path = Path(self.temp_dir.name).resolve()

        # Create dummy test files
        self.doc_file = self.root_path / "annual_report_2024.pdf"
        self.doc_file.write_text("dummy pdf content", encoding="utf-8")

        self.img_file = self.root_path / "screenshot_01.png"
        self.img_file.write_text("dummy png content", encoding="utf-8")

        self.notes_file = self.root_path / "meeting_notes.txt"
        self.notes_file.write_text("dummy notes content", encoding="utf-8")

        # Custom history file for safety testing
        self.history_file = self.root_path / ".test_history.json"
        self.logger = TransactionLogger(log_path=self.history_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_finder_fuzzy_search(self):
        """Tests fuzzy directory search matching."""
        finder = FileFinder()
        results = finder.search(query="report", start_dir=str(self.root_path))
        self.assertTrue(len(results) >= 1)
        self.assertEqual(results[0].name, "annual_report_2024.pdf")

    def test_renamer_single(self):
        """Tests single file rename and transaction logging."""
        action = FileRenamer.prepare_single_rename(
            source_path=self.doc_file,
            new_name="financial_summary_2024.pdf"
        )
        self.assertEqual(action.status, "OK")

        successful, failed = FileRenamer.execute_rename_actions([action])
        self.assertEqual(len(successful), 1)
        self.assertFalse(self.doc_file.exists())
        
        new_path = self.root_path / "financial_summary_2024.pdf"
        self.assertTrue(new_path.exists())

        # Test transaction undo
        session_id = self.logger.log_session(successful)
        self.assertTrue(session_id.startswith("session_"))

        reversed_count, undo_errors = self.logger.undo_last_session()
        self.assertEqual(reversed_count, 1)
        self.assertEqual(len(undo_errors), 0)
        self.assertTrue(self.doc_file.exists())
        self.assertFalse(new_path.exists())

    def test_mover_relocation(self):
        """Tests file relocation and undo rollback."""
        target_dir = self.root_path / "Docs"
        target_dir.mkdir(exist_ok=True)

        actions = FileMover.prepare_move_actions(
            sources=[self.img_file],
            target_dir=target_dir
        )
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].status, "OK")

        successful, failed = FileMover.execute_move_actions(actions)
        self.assertEqual(len(successful), 1)
        self.assertFalse(self.img_file.exists())
        
        moved_file = target_dir / "screenshot_01.png"
        self.assertTrue(moved_file.exists())

        # Rollback via undo logger
        self.logger.log_session(successful)
        reversed_count, undo_errors = self.logger.undo_last_session()
        self.assertEqual(reversed_count, 1)
        self.assertTrue(self.img_file.exists())

    def test_slash_command_router(self):
        """Tests SlashCommandRouter dispatching."""
        router = SlashCommandRouter()
        repl = AutobotREPL(model_name="Gemma 4B (Local)")

        # Verify router detects slash inputs
        self.assertTrue(router.is_slash_command("/status"))
        self.assertTrue(router.is_slash_command("/locate report"))
        self.assertFalse(router.is_slash_command("move report to Archive"))

        # Test dispatching
        self.assertTrue(router.dispatch("/status", repl))
        self.assertTrue(router.dispatch("/help", repl))
        self.assertTrue(router.dispatch("/model cloud", repl))
        self.assertTrue("Cloud LLM" in repl.model_name)

        # Test /key command
        self.assertTrue(router.dispatch("/key sk-testkey123456", repl))
        import config
        self.assertEqual(config.LLM_API_KEY, "sk-testkey123456")

        # Clean up test key
        if config.CONFIG_FILE_PATH.exists():
            config.CONFIG_FILE_PATH.unlink()
        config.LLM_API_KEY = ""

    def test_default_model_detection(self):
        """Verifies default REPL model detection handles absence of models cleanly."""
        from ui.repl import detect_active_model
        model = detect_active_model()
        self.assertEqual(model, "No model available")
        repl = AutobotREPL()
        self.assertEqual(repl.model_name, "No model available")

    def test_interactive_guardrails(self):
        """Tests InteractiveUI confirmation, missing directory creation, and undo guardrails."""
        from ui.interactive import InteractiveUI
        from core.mover import MoveAction

        # Test prompt_create_destination with auto-confirm yes
        non_existent_dir = self.root_path / "NonExistent"
        self.assertTrue(InteractiveUI.prompt_create_destination(non_existent_dir, yes=True))
        FileMover.create_destination_directory(non_existent_dir, user_confirmed=True)
        self.assertTrue(non_existent_dir.exists())

        # Test confirm_action_execution with dry_run
        test_action = MoveAction(
            source_path=self.doc_file,
            target_dir=non_existent_dir,
            target_path=non_existent_dir / self.doc_file.name,
            is_dir=False,
            status="OK"
        )
        # dry_run returns False because execution is prevented
        self.assertFalse(InteractiveUI.confirm_action_execution([test_action], dry_run=True, yes=True))
        # yes=True with dry_run=False returns True
        self.assertTrue(InteractiveUI.confirm_action_execution([test_action], dry_run=False, yes=True))

        # Test prompt_undo_confirmation
        self.assertTrue(InteractiveUI.prompt_undo_confirmation("session_123", 2, yes=True))


if __name__ == "__main__":
    unittest.main()

