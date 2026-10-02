"""
Core Mover Engine for cliagent.
Handles single and multiple file/folder moving, target directory verification,
missing directory prompts, collision checks, and cross-volume file relocation.
"""
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass

from config import resolve_user_path


@dataclass
class MoveAction:
    """
    Represents a proposed or executed move action for a single file or directory.
    """
    source_path: Path
    target_dir: Path
    target_path: Path
    is_dir: bool
    status: str  # "OK", "MISSING_DESTINATION", "COLLISION", "SOURCE_NOT_FOUND", "NO_CHANGE"
    message: str = ""
    requires_dest_creation: bool = False

    def to_dict(self) -> Dict:
        return {
            "source": str(self.source_path.resolve()),
            "target_dir": str(self.target_dir.resolve()),
            "target_path": str(self.target_path.resolve()),
            "is_dir": self.is_dir,
            "status": self.status,
            "message": self.message,
            "requires_dest_creation": self.requires_dest_creation,
        }


class FileMover:
    """
    Handles moving single and multiple files/folders with safety checks.
    """

    @staticmethod
    def prepare_move_actions(
        sources: List[Path],
        target_dir: Path,
        custom_target_name: Optional[str] = None
    ) -> List[MoveAction]:
        """
        Validates and prepares MoveAction objects for a batch of files/folders.

        :param sources: List of source file/folder paths to move
        :param target_dir: Target directory path where files should be moved
        :param custom_target_name: Optional override filename (only used when moving a single item)
        :return: List of MoveAction objects
        """
        resolved_target_dir = resolve_user_path(target_dir)
        dest_exists = resolved_target_dir.exists() and resolved_target_dir.is_dir()
        
        actions: List[MoveAction] = []
        proposed_target_paths = set()

        for idx, src in enumerate(sources):
            source_path = Path(src).resolve()

            if not source_path.exists():
                actions.append(
                    MoveAction(
                        source_path=source_path,
                        target_dir=resolved_target_dir,
                        target_path=resolved_target_dir / source_path.name,
                        is_dir=False,
                        status="SOURCE_NOT_FOUND",
                        message="Source file or folder does not exist.",
                        requires_dest_creation=not dest_exists
                    )
                )
                continue

            # Target filename determination
            target_name = source_path.name
            if custom_target_name and len(sources) == 1:
                target_name = custom_target_name

            target_path = resolved_target_dir / target_name
            is_dir = source_path.is_dir()

            # Check for move to self / same directory
            if source_path == target_path:
                actions.append(
                    MoveAction(
                        source_path=source_path,
                        target_dir=resolved_target_dir,
                        target_path=target_path,
                        is_dir=is_dir,
                        status="NO_CHANGE",
                        message="Source and destination paths are identical.",
                        requires_dest_creation=not dest_exists
                    )
                )
                continue

            # Determine status
            status = "OK"
            msg = "Ready to move."
            requires_creation = not dest_exists

            if not dest_exists:
                status = "MISSING_DESTINATION"
                msg = f"Target directory '{resolved_target_dir}' does not exist."
            elif target_path.exists() or target_path in proposed_target_paths:
                status = "COLLISION"
                msg = f"A file or folder named '{target_name}' already exists in destination."
            else:
                proposed_target_paths.add(target_path)

            actions.append(
                MoveAction(
                    source_path=source_path,
                    target_dir=resolved_target_dir,
                    target_path=target_path,
                    is_dir=is_dir,
                    status=status,
                    message=msg,
                    requires_dest_creation=requires_creation
                )
            )

        return actions

    @staticmethod
    def create_destination_directory(target_dir: Path, user_confirmed: bool) -> bool:
        """
        Creates the target directory ONLY if user_confirmed is True (user agreed with 'y' or 'Y').
        """
        if not user_confirmed:
            return False

        try:
            target_dir = Path(target_dir).resolve()
            target_dir.mkdir(parents=True, exist_ok=True)
            return True
        except Exception:
            return False

    @staticmethod
    def execute_move_actions(actions: List[MoveAction]) -> Tuple[List[MoveAction], List[MoveAction]]:
        """
        Executes approved MoveAction items on disk using shutil.move.
        Returns (successful_actions, failed_actions).
        """
        successful: List[MoveAction] = []
        failed: List[MoveAction] = []

        for action in actions:
            if action.status != "OK":
                failed.append(action)
                continue

            try:
                # Ensure target parent directory exists
                if not action.target_dir.exists():
                    action.status = "MISSING_DESTINATION"
                    action.message = f"Destination directory '{action.target_dir}' does not exist."
                    failed.append(action)
                    continue

                # Move file or folder using shutil.move (handles cross-drive moves cleanly)
                shutil.move(str(action.source_path), str(action.target_path))
                successful.append(action)
            except Exception as e:
                action.status = "ERROR"
                action.message = str(e)
                failed.append(action)

        return successful, failed

    @classmethod
    def prepare_move(
        cls,
        query: str,
        target_dir: Union[str, Path],
        start_dir: Union[str, Path] = ".",
        extensions: Optional[List[str]] = None,
    ) -> List[MoveAction]:
        """
        Locates items matching query using FileFinder and prepares MoveAction objects.
        """
        from core.finder import FileFinder
        finder = FileFinder()
        resolved_start = resolve_user_path(start_dir)
        resolved_target = resolve_user_path(target_dir)
        results = finder.search(query=query, start_dir=resolved_start, extensions=extensions)
        sources = [r.path for r in results]
        return cls.prepare_move_actions(sources=sources, target_dir=resolved_target)

    execute_move = execute_move_actions
