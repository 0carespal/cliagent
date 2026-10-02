"""
End-to-End Automated Test Suite for Autobot CLI Agent.
Validates Finder, Renamer, Mover, Safety undo log, Theme, REPL session, and Slash Command Router.
"""

import os
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
        from unittest.mock import patch
        from ui.repl import detect_active_model
        with patch("config.load_user_config", return_value={}), \
             patch("ai.local_llm.LocalLLMClient.is_available", return_value=False):
            model = detect_active_model()
            self.assertEqual(model, "No model available")
            repl = AutobotREPL(model_name=model)
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

    def test_model_discovery_and_selection(self):
        """Tests Phase 17 local model discovery and /model slash commands."""
        from ai.local_llm import LocalLLMClient
        local_client = LocalLLMClient()
        installed = local_client.list_installed_models()
        self.assertIsInstance(installed, list)

        router = SlashCommandRouter()
        repl = AutobotREPL(model_name="No model available")

        # Test /model list
        self.assertTrue(router.dispatch("/model list", repl))
        # Test /models alias
        self.assertTrue(router.dispatch("/models", repl))
        # Test /model local
        self.assertTrue(router.dispatch("/model local", repl))
        self.assertTrue("Local LLM" in repl.model_name)

        # Clean up test config
        import config
        if config.CONFIG_FILE_PATH.exists():
            config.CONFIG_FILE_PATH.unlink()

    def test_fnmatch_wildcard_matching(self):
        """Tests Phase 18 fnmatch wildcard and glob precision matching in FileFinder."""
        finder = FileFinder()

        # Wildcard extension search: *.pdf should match annual_report_2024.pdf with score 100.0
        pdf_results = finder.search("*.pdf", start_dir=self.root_path)
        self.assertEqual(len(pdf_results), 1)
        self.assertEqual(pdf_results[0].name, "annual_report_2024.pdf")
        self.assertEqual(pdf_results[0].match_score, 100.0)

        # Wildcard substring glob: *report*
        report_results = finder.search("*report*", start_dir=self.root_path)
        self.assertEqual(len(report_results), 1)
        self.assertEqual(report_results[0].name, "annual_report_2024.pdf")
        self.assertEqual(report_results[0].match_score, 100.0)

        # Wildcard single char ?: screenshot_??.png
        png_results = finder.search("screenshot_??.png", start_dir=self.root_path)
        self.assertEqual(len(png_results), 1)
        self.assertEqual(png_results[0].name, "screenshot_01.png")
        self.assertEqual(png_results[0].match_score, 100.0)

        # Non-matching wildcard should return empty list (no false positive fuzzy matches)
        empty_results = finder.search("*.xlsx", start_dir=self.root_path)
        self.assertEqual(len(empty_results), 0)

        # Test FileMover with wildcard query
        target_dir = self.root_path / "PngFolder"
        move_actions = FileMover.prepare_move("*.png", target_dir=target_dir, start_dir=self.root_path)
        self.assertEqual(len(move_actions), 1)
        self.assertEqual(move_actions[0].source_path.name, "screenshot_01.png")

        # Test FileRenamer with wildcard query
        rename_actions = FileRenamer.prepare_single_rename(
            query="*report*",
            new_name="annual_report_final.pdf",
            start_dir=self.root_path
        )
        self.assertEqual(len(rename_actions), 1)
        self.assertEqual(rename_actions[0].old_name, "annual_report_2024.pdf")
        self.assertEqual(rename_actions[0].new_name, "annual_report_final.pdf")

    def test_case_preserving_rename_and_cross_drive_undo(self):
        """Tests Phase 19 case-preserving renaming and cross-drive undo rollback."""
        # 1. Create a file with lowercase name
        sample_file = self.root_path / "readme.md"
        sample_file.write_text("sample content", encoding="utf-8")

        # 2. Prepare single case-only rename: readme.md -> README.md
        action = FileRenamer.prepare_single_rename(sample_file, "README.md")
        self.assertEqual(action.status, "OK")
        self.assertEqual(action.new_name, "README.md")

        # 3. Execute rename
        successful, failed = FileRenamer.execute_rename_actions([action])
        self.assertEqual(len(successful), 1)
        self.assertEqual(len(failed), 0)

        # 4. Verify disk name has new case
        dir_files = os.listdir(self.root_path)
        self.assertIn("README.md", dir_files)

        # 5. Log transaction and test undo
        session_id = self.logger.log_session(successful)
        reversed_count, errors = self.logger.undo_last_session()
        self.assertEqual(reversed_count, 1)
        self.assertEqual(len(errors), 0)
        self.assertIn("readme.md", os.listdir(self.root_path))

        # 6. Test bulk case transformation does not trigger false collision
        bulk_file1 = self.root_path / "doc_one.txt"
        bulk_file2 = self.root_path / "doc_two.txt"
        bulk_file1.write_text("one", encoding="utf-8")
        bulk_file2.write_text("two", encoding="utf-8")

        bulk_actions = FileRenamer.prepare_bulk_rename(
            items=[bulk_file1, bulk_file2],
            case_format="upper"
        )
        self.assertEqual(len(bulk_actions), 2)
        for a in bulk_actions:
            self.assertEqual(a.status, "OK")
            self.assertIn("case modification", a.message)

        succ, fail = FileRenamer.execute_rename_actions(bulk_actions)
        self.assertEqual(len(succ), 2)
        self.assertEqual(len(fail), 0)
        self.assertIn("DOC_ONE.txt", os.listdir(self.root_path))
        self.assertIn("DOC_TWO.txt", os.listdir(self.root_path))

    def test_resolve_user_path(self):
        """Tests smart path alias resolution for system folders, home (~), and relative dirs."""
        from config import resolve_user_path
        home = Path.home().resolve()

        # Test ~ expansion
        self.assertEqual(resolve_user_path("~"), home)
        self.assertEqual(resolve_user_path("~/Projects"), home / "Projects")

        # Test common OS shortcuts (case-insensitive)
        self.assertEqual(resolve_user_path("downloads"), (home / "Downloads").resolve())
        self.assertEqual(resolve_user_path("Desktop"), (home / "Desktop").resolve())
        self.assertEqual(resolve_user_path("Documents/Reports"), (home / "Documents" / "Reports").resolve())

        # Test relative path with base_dir override
        sub_folder = self.root_path / "SubFolder"
        self.assertEqual(resolve_user_path("SubFolder", base_dir=self.root_path), sub_folder.resolve())

        # Test absolute path preservation
        self.assertEqual(resolve_user_path(str(self.root_path)), self.root_path)

    def test_renamer_camel_and_title_case(self):
        """Tests camelCase and TitleCase bulk transformations."""
        f1 = self.root_path / "my_user_profile.py"
        f2 = self.root_path / "parse_csv_data.py"
        f1.write_text("profile", encoding="utf-8")
        f2.write_text("csv", encoding="utf-8")

        # Test camelCase
        camel_actions = FileRenamer.prepare_bulk_rename(
            items=[f1],
            case_format="camel"
        )
        self.assertEqual(len(camel_actions), 1)
        self.assertEqual(camel_actions[0].new_name, "myUserProfile.py")

        # Test TitleCase
        title_actions = FileRenamer.prepare_bulk_rename(
            items=[f2],
            case_format="title"
        )
        self.assertEqual(len(title_actions), 1)
        self.assertEqual(title_actions[0].new_name, "ParseCsvData.py")

    def test_cd_slash_command(self):
        """Tests /cd command with path alias resolution."""
        router = SlashCommandRouter()
        repl = AutobotREPL()

        sub_dir = self.root_path / "TestWorkspace"
        sub_dir.mkdir(exist_ok=True)

        # /cd to relative folder
        repl.cwd = self.root_path
        self.assertTrue(router.dispatch("/cd TestWorkspace", repl))
        self.assertEqual(repl.cwd, sub_dir.resolve())

        # /cd to ~
        self.assertTrue(router.dispatch("/cd ~", repl))
        self.assertEqual(repl.cwd, Path.home().resolve())

    def test_sanitize_json_response_resilience(self):
        """Tests robust JSON extraction from LLM outputs with markdown fences and conversational preambles."""
        import json
        from ai.base import sanitize_json_response

        # 1. Clean JSON
        raw1 = '{"action": "locate", "query": "*.pdf"}'
        self.assertEqual(json.loads(sanitize_json_response(raw1))["action"], "locate")

        # 2. Markdown fence with ```json
        raw2 = '```json\n{"action": "rename", "query": "test", "new_name": "sample"}\n```'
        self.assertEqual(json.loads(sanitize_json_response(raw2))["action"], "rename")

        # 3. Conversational preamble and closing remarks around markdown fence
        raw3 = (
            "Certainly! Here is the JSON intent object you requested:\n"
            "```json\n"
            '{"action": "move", "query": "photo", "target_dir": "Pictures"}\n'
            "```\n"
            "Please let me know if you need anything else!"
        )
        parsed3 = json.loads(sanitize_json_response(raw3))
        self.assertEqual(parsed3["action"], "move")
        self.assertEqual(parsed3["target_dir"], "Pictures")

        # 4. Raw text without code fences
        raw4 = 'Here is the result: {"action": "locate", "query": "report"} - hope this helps.'
        parsed4 = json.loads(sanitize_json_response(raw4))
        self.assertEqual(parsed4["query"], "report")

    def test_transaction_history_retrieval(self):
        """Tests TransactionLogger get_history method and limit slicing."""
        from core.renamer import RenameAction

        action1 = RenameAction(source_path=self.doc_file, target_path=self.root_path / "doc1.pdf", old_name=self.doc_file.name, new_name="doc1.pdf", is_dir=False, status="OK")
        action2 = RenameAction(source_path=self.img_file, target_path=self.root_path / "img1.png", old_name=self.img_file.name, new_name="img1.png", is_dir=False, status="OK")
        action3 = RenameAction(source_path=self.notes_file, target_path=self.root_path / "notes1.txt", old_name=self.notes_file.name, new_name="notes1.txt", is_dir=False, status="OK")

        self.logger.log_session([action1])
        self.logger.log_session([action2])
        self.logger.log_session([action3])

        # Test limit=2
        history_2 = self.logger.get_history(limit=2)
        self.assertEqual(len(history_2), 2)

        # Test all history
        history_all = self.logger.get_history(limit=10)
        self.assertEqual(len(history_all), 3)

    def test_history_slash_command(self):
        """Tests /history slash command dispatch and table rendering."""
        router = SlashCommandRouter()
        repl = AutobotREPL()

        # Should dispatch cleanly even with no sessions or some sessions
        self.assertTrue(router.dispatch("/history", repl))
        self.assertTrue(router.dispatch("/history 5", repl))

    def test_model_no_args_does_not_mutate(self):
        """Tests that typing /model without arguments renders available models without silently mutating active model."""
        router = SlashCommandRouter()
        repl = AutobotREPL(model_name="Custom Model")
        self.assertTrue(router.dispatch("/model", repl))
        self.assertEqual(repl.model_name, "Custom Model")
        self.assertTrue(router.dispatch("/models", repl))
        self.assertEqual(repl.model_name, "Custom Model")

    def test_local_model_prefers_4b(self):
        """Tests that LocalLLMClient automatically prefers lighter 4B models when multiple models are installed."""
        from unittest.mock import patch
        from ai.local_llm import LocalLLMClient
        client = LocalLLMClient()
        with patch.object(client, "list_installed_models", return_value=["qwen3.5:latest", "qwen3.5:9b", "qwen3.5:4b"]):
            self.assertEqual(client.resolve_model_name(), "qwen3.5:4b")

    def test_intent_parser_timeout_error_reporting(self):
        """Tests that AIIntentParser reports specific error details rather than generic provider None."""
        from unittest.mock import patch
        from ai.intent_parser import AIIntentParser
        parser = AIIntentParser()
        with patch.object(parser.local_client, "is_available", return_value=True), \
             patch.object(parser.local_client, "parse_intent", return_value=None), \
             patch.object(parser.cloud_client, "is_available", return_value=False):
            parser.local_client.last_error = "Local model 'qwen3.5:latest' timed out after 90s"
            result, err = parser.parse("find files")
            self.assertIsNone(result)
            self.assertIn("timed out after 90s", err)

    def test_explicit_relative_path_resolution(self):
        """Tests that explicit ./ or .\\ prefixes resolve to current directory and do not alias to home folder."""
        from config import resolve_user_path
        res_dot_slash = resolve_user_path("./downloads", base_dir=self.root_path)
        self.assertEqual(res_dot_slash, (self.root_path / "downloads").resolve())
        res_dot_backslash = resolve_user_path(".\\desktop", base_dir=self.root_path)
        self.assertEqual(res_dot_backslash, (self.root_path / "desktop").resolve())

    def test_mover_recursion_prevention(self):
        """Tests that moving a folder into itself or a subdirectory of itself is prevented."""
        parent_dir = self.root_path / "ParentFolder"
        parent_dir.mkdir(exist_ok=True)
        child_dir = parent_dir / "ChildFolder"
        child_dir.mkdir(exist_ok=True)

        actions = FileMover.prepare_move_actions(
            sources=[parent_dir],
            target_dir=child_dir
        )
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].status, "INVALID_MOVE")
        self.assertIn("Cannot move folder", actions[0].message)

    def test_mover_batch_internal_collision_missing_dest(self):
        """Tests that duplicate target filenames in a single move batch are flagged as collisions even if target dir is missing."""
        dir1 = self.root_path / "d1"
        dir2 = self.root_path / "d2"
        dir1.mkdir(exist_ok=True)
        dir2.mkdir(exist_ok=True)
        f1 = dir1 / "same_name.txt"
        f2 = dir2 / "same_name.txt"
        f1.write_text("one")
        f2.write_text("two")

        missing_target = self.root_path / "NonExistentDestFolder"

        actions = FileMover.prepare_move_actions(
            sources=[f1, f2],
            target_dir=missing_target
        )
        self.assertEqual(len(actions), 2)
        # First file requires destination creation
        self.assertEqual(actions[0].status, "MISSING_DESTINATION")
        # Second file targeting same path in same batch should be flagged COLLISION
        self.assertEqual(actions[1].status, "COLLISION")

    def test_undo_discards_dead_session(self):
        """Tests that an un-restorable session (targets missing) is popped from undo stack to avoid jamming."""
        from core.renamer import RenameAction
        fake_action = RenameAction(
            source_path=self.root_path / "ghost_src.txt",
            target_path=self.root_path / "ghost_tgt.txt",
            old_name="ghost_src.txt",
            new_name="ghost_tgt.txt",
            is_dir=False,
            status="OK"
        )
        # Log a session with non-existent target
        self.logger.log_session([fake_action])
        initial_history_len = len(self.logger._load_history())

        reversed_count, errors = self.logger.undo_last_session()
        self.assertEqual(reversed_count, 0)
        # Session should be popped so undo stack is not jammed
        new_history_len = len(self.logger._load_history())
        self.assertEqual(new_history_len, initial_history_len - 1)


if __name__ == "__main__":
    unittest.main()


