"""
Core Renamer Engine for cliagent.
Handles single file/folder renaming, bulk renaming with patterns, case formatting,
sequence numbering, and collision checking.
"""
import re
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Any
from dataclasses import dataclass

from config import resolve_user_path


@dataclass
class RenameAction:
    """
    Represents a proposed or executed rename action for a single file/folder.
    """
    source_path: Path
    target_path: Path
    old_name: str
    new_name: str
    is_dir: bool
    status: str  # "OK", "COLLISION", "NO_CHANGE", "INVALID_NAME"
    message: str = ""

    def to_dict(self) -> Dict:
        return {
            "source": str(self.source_path.resolve()),
            "target": str(self.target_path.resolve()),
            "old_name": self.old_name,
            "new_name": self.new_name,
            "is_dir": self.is_dir,
            "status": self.status,
            "message": self.message,
        }


class FileRenamer:
    """
    Handles single and bulk renaming operations with safety checks.
    """

    @classmethod
    def _prepare_single_action(cls, source_path: Path, new_name: str) -> RenameAction:
        """Helper validating and creating a single RenameAction object."""
        source = Path(source_path).resolve()
        if not source.exists():
            return RenameAction(
                source_path=source,
                target_path=source,
                old_name=source.name,
                new_name=new_name,
                is_dir=False,
                status="INVALID_NAME",
                message="Source file or folder does not exist."
            )

        # Build target path in the same parent directory
        target = source.parent / new_name

        if source.name == new_name:
            return RenameAction(
                source_path=source,
                target_path=target,
                old_name=source.name,
                new_name=new_name,
                is_dir=source.is_dir(),
                status="NO_CHANGE",
                message="New name is identical to current name."
            )

        # Case-only rename check on case-insensitive filesystems (e.g. Windows/macOS)
        is_case_only = (source.name.lower() == new_name.lower())

        if target.exists() and not is_case_only:
            return RenameAction(
                source_path=source,
                target_path=target,
                old_name=source.name,
                new_name=new_name,
                is_dir=source.is_dir(),
                status="COLLISION",
                message=f"Target file '{new_name}' already exists in destination."
            )

        return RenameAction(
            source_path=source,
            target_path=target,
            old_name=source.name,
            new_name=new_name,
            is_dir=source.is_dir(),
            status="OK",
            message="Ready to rename (case modification)." if is_case_only else "Ready to rename."
        )

    @classmethod
    def prepare_single_rename(
        cls,
        source_path: Optional[Union[str, Path]] = None,
        new_name: str = "",
        query: Optional[str] = None,
        start_dir: Union[str, Path] = "."
    ) -> Any:
        """
        Validates and prepares a single file/folder rename action.
        If called with (source_path, new_name), returns RenameAction.
        If called with (query, new_name, start_dir), returns List[RenameAction].
        """
        if query:
            from core.finder import FileFinder
            finder = FileFinder()
            resolved_start = resolve_user_path(start_dir)
            results = finder.search(query=query, start_dir=resolved_start, max_results=1)
            if not results:
                return []
            return [cls._prepare_single_action(results[0].path, new_name)]

        if source_path:
            return cls._prepare_single_action(Path(source_path), new_name)

        raise ValueError("Either source_path or query must be provided to prepare_single_rename")

    @classmethod
    def prepare_bulk_rename(
        cls,
        items: Optional[List[Path]] = None,
        prefix: str = "",
        suffix: str = "",
        find_str: str = "",
        replace_str: str = "",
        case_format: Optional[str] = None,  # "snake", "kebab", "camel", "title", "lower", "upper"
        sequence_prefix: Optional[str] = None,  # e.g., "vacation_" -> vacation_01.jpg
        start_number: int = 1,
        query: Optional[str] = None,
        start_dir: Union[str, Path] = ".",
        case_type: Optional[str] = None,
        seq_pattern: Optional[str] = None,
    ) -> List[RenameAction]:
        """
        Generates a list of proposed RenameActions for bulk renaming.
        Supports passing items directly or finding them via query.
        """
        if items is None and query:
            from core.finder import FileFinder
            finder = FileFinder()
            resolved_start = resolve_user_path(start_dir)
            results = finder.search(query=query, start_dir=resolved_start)
            items = [r.path for r in results]
        elif items is None:
            items = []

        active_case = (case_type or case_format or "").lower()
        active_seq = seq_pattern if seq_pattern is not None else sequence_prefix
        actions: List[RenameAction] = []
        # Track proposed target names in this batch to detect internal collisions
        proposed_targets = set()

        for idx, item in enumerate(items):
            item_path = Path(item).resolve()
            if not item_path.exists():
                continue

            stem = item_path.stem  # Filename without extension
            ext = item_path.suffix  # File extension including dot (.jpg)
            is_dir = item_path.is_dir()

            # If item is a directory, there is no extension; full name is stem
            if is_dir:
                stem = item_path.name
                ext = ""

            new_stem = stem

            # 1. Apply Find & Replace
            if find_str:
                new_stem = new_stem.replace(find_str, replace_str)

            # 2. Apply Case Transformation
            if active_case == "lower":
                new_stem = new_stem.lower()
            elif active_case == "upper":
                new_stem = new_stem.upper()
            elif active_case == "snake":
                new_stem = FileRenamer._to_snake_case(new_stem)
            elif active_case == "kebab":
                new_stem = FileRenamer._to_kebab_case(new_stem)
            elif active_case in ("camel", "camelcase"):
                new_stem = FileRenamer._to_camel_case(new_stem)
            elif active_case in ("title", "titlecase", "pascal"):
                new_stem = FileRenamer._to_title_case(new_stem)

            # 3. Apply Prefix / Suffix
            if prefix:
                new_stem = f"{prefix}{new_stem}"
            if suffix:
                new_stem = f"{new_stem}{suffix}"

            # 4. Apply Sequence Numbering (Overrides stem if active_seq is given)
            if active_seq is not None:
                pad_width = max(2, len(str(start_number + len(items) - 1)))
                num_str = str(start_number + idx).zfill(pad_width)  # 01, 02, 03... or 001..100
                new_stem = f"{active_seq}{num_str}"

            # Reconstruct full new filename
            new_filename = f"{new_stem}{ext}"
            target_path = item_path.parent / new_filename

            # Check for collisions
            status = "OK"
            msg = "Ready to rename."

            is_case_only = (item_path.name.lower() == new_filename.lower() and item_path.name != new_filename)
            normalized_target = str(target_path).lower()

            if item_path.name == new_filename:
                status = "NO_CHANGE"
                msg = "Name unchanged."
            elif (target_path.exists() and not is_case_only) or normalized_target in proposed_targets:
                status = "COLLISION"
                msg = f"Collision detected for target name '{new_filename}'."
            else:
                proposed_targets.add(normalized_target)
                if is_case_only:
                    msg = "Ready to rename (case modification)."

            actions.append(
                RenameAction(
                    source_path=item_path,
                    target_path=target_path,
                    old_name=item_path.name,
                    new_name=new_filename,
                    is_dir=is_dir,
                    status=status,
                    message=msg
                )
            )

        return actions

    @staticmethod
    def execute_rename_actions(actions: List[RenameAction]) -> Tuple[List[RenameAction], List[RenameAction]]:
        """
        Executes approved RenameAction items on disk.
        Supports case-only renaming on case-insensitive filesystems using two-step rename.
        Returns (successful_actions, failed_actions).
        """
        successful: List[RenameAction] = []
        failed: List[RenameAction] = []

        for action in actions:
            if action.status != "OK":
                failed.append(action)
                continue

            try:
                # Check for case-only rename on case-insensitive filesystems (Windows/macOS)
                is_case_only = (
                    action.source_path.parent == action.target_path.parent
                    and action.source_path.name.lower() == action.target_path.name.lower()
                    and action.source_path.name != action.target_path.name
                )
                if is_case_only:
                    # Two-step rename using unique temp file to avoid WinError 183
                    temp_path = action.source_path.with_name(f"{action.source_path.name}.__tmp_{uuid.uuid4().hex[:8]}")
                    action.source_path.rename(temp_path)
                    temp_path.rename(action.target_path)
                else:
                    action.source_path.rename(action.target_path)

                successful.append(action)
            except Exception as e:
                action.status = "ERROR"
                action.message = str(e)
                failed.append(action)

        return successful, failed

    execute_rename = execute_rename_actions

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Converts string to snake_case (e.g. 'My File Name' -> 'my_file_name')."""
        s = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
        s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
        s = re.sub(r'[\s\-\.]+', '_', s).strip('_')
        return s.lower()

    @staticmethod
    def _to_kebab_case(name: str) -> str:
        """Converts string to kebab-case (e.g. 'My File Name' -> 'my-file-name')."""
        s = FileRenamer._to_snake_case(name)
        return s.replace('_', '-')

    @staticmethod
    def _to_camel_case(name: str) -> str:
        """Converts string to camelCase (e.g. 'my_file_name' -> 'myFileName')."""
        s = FileRenamer._to_snake_case(name)
        parts = [p for p in s.split('_') if p]
        if not parts:
            return ""
        return parts[0] + ''.join(word.capitalize() for word in parts[1:])

    @staticmethod
    def _to_title_case(name: str) -> str:
        """Converts string to TitleCase / PascalCase (e.g. 'my_file_name' -> 'MyFileName')."""
        s = FileRenamer._to_snake_case(name)
        parts = [p for p in s.split('_') if p]
        return ''.join(word.capitalize() for word in parts)
