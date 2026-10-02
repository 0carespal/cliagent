"""
Core Search and Finder Module for cliagent.
Handles recursive directory traversal, directory pruning (ignoring junk folders),
fuzzy string matching via rapidfuzz, and file metadata filtering (extension, size, type).
"""
import os
import fnmatch
from pathlib import Path
from typing import List, Dict, Optional, Set, Union
from dataclasses import dataclass
from rapidfuzz import fuzz

from config import DEFAULT_IGNORED_DIRS, resolve_user_path


@dataclass
class SearchResult:
    """
    Data structure representing a single file or directory search match.
    """
    path: Path
    name: str
    is_dir: bool
    size_bytes: int
    match_score: float
    parent_dir: Path

    def to_dict(self) -> Dict:
        """Converts the result to a dictionary for easy serialization."""
        return {
            "path": str(self.path.resolve()),
            "name": self.name,
            "is_dir": self.is_dir,
            "size_bytes": self.size_bytes,
            "match_score": round(self.match_score, 2),
            "location": str(self.parent_dir.resolve()),
        }


class FileFinder:
    """
    High-performance file and folder finder with fuzzy matching and smart directory pruning.
    """

    def __init__(self, ignored_dirs: Optional[Set[str]] = None):
        """
        Initializes the finder with a set of ignored directory names.
        """
        self.ignored_dirs = set(ignored_dirs) if ignored_dirs else DEFAULT_IGNORED_DIRS
        # Lowercase set for fast case-insensitive lookup
        self.ignored_dirs_lower = {d.lower() for d in self.ignored_dirs}

    def search(
        self,
        query: str,
        start_dir: Union[str, Path] = ".",
        min_score: float = 60.0,
        extensions: Optional[List[str]] = None,
        min_size_mb: Optional[float] = None,
        max_size_mb: Optional[float] = None,
        search_type: str = "all",  # "files", "folders", or "all"
        max_results: Optional[int] = None,
    ) -> List[SearchResult]:
        """
        Recursively searches start_dir for files/folders matching the query.

        :param query: Search string (e.g. "report", "invoice")
        :param start_dir: Root directory to begin search from
        :param min_score: Minimum fuzzy match score (0-100) to consider a match
        :param extensions: List of target extensions (e.g. [".pdf", ".png"])
        :param min_size_mb: Minimum file size in megabytes
        :param max_size_mb: Maximum file size in megabytes
        :param search_type: Type of targets to return ("files", "folders", "all")
        :param max_results: Cap total matches returned (optional)
        :return: List of SearchResult objects sorted by match_score descending
        """
        root_path = resolve_user_path(start_dir)
        if not root_path.exists():
            raise FileNotFoundError(f"Search root directory does not exist: {root_path}")

        # Normalize extension filters to lowercase with leading dots (e.g., ".pdf")
        normalized_exts = None
        if extensions:
            normalized_exts = {
                ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                for ext in extensions
            }

        results: List[SearchResult] = []

        # Convert sizes to bytes for direct comparison
        min_bytes = min_size_mb * 1024 * 1024 if min_size_mb is not None else None
        max_bytes = max_size_mb * 1024 * 1024 if max_size_mb is not None else None

        # Recursively walk the directory tree
        for current_root, dirnames, filenames in os.walk(root_path, topdown=True):
            current_path = Path(current_root)

            # -------------------------------------------------------------
            # STEP 1: DIRECTORY PRUNING (CRITICAL SPEED OPTIMIZATION)
            # Modifying `dirnames` in-place prevents os.walk from entering
            # ignored system/junk directories like .git, node_modules, AppData.
            # -------------------------------------------------------------
            dirnames[:] = [
                d for d in dirnames
                if d.lower() not in self.ignored_dirs_lower
            ]

            # -------------------------------------------------------------
            # STEP 2: EVALUATE DIRECTORIES (if search_type is "folders" or "all")
            # -------------------------------------------------------------
            if search_type in ("folders", "all"):
                for dirname in dirnames:
                    full_dir_path = current_path / dirname
                    try:
                        rel_dir = str(full_dir_path.relative_to(root_path)).replace("\\", "/")
                    except ValueError:
                        rel_dir = dirname
                    score = self._compute_score(query, dirname, rel_path=rel_dir)

                    if score >= min_score:
                        results.append(
                            SearchResult(
                                path=full_dir_path,
                                name=dirname,
                                is_dir=True,
                                size_bytes=0,  # Directory size omitted for speed
                                match_score=score,
                                parent_dir=current_path,
                            )
                        )

            # -------------------------------------------------------------
            # STEP 3: EVALUATE FILES (if search_type is "files" or "all")
            # -------------------------------------------------------------
            if search_type in ("files", "all"):
                for filename in filenames:
                    file_path = current_path / filename

                    # Filter by extension if specified
                    if normalized_exts and file_path.suffix.lower() not in normalized_exts:
                        continue

                    # Filter by size if specified
                    file_size = 0
                    try:
                        file_size = file_path.stat().st_size
                    except (PermissionError, FileNotFoundError):
                        # Skip files with restricted OS permissions or broken symlinks
                        continue

                    if min_bytes is not None and file_size < min_bytes:
                        continue
                    if max_bytes is not None and file_size > max_bytes:
                        continue

                    # Compute similarity score (wildcard glob or fuzzy match)
                    try:
                        rel_file = str(file_path.relative_to(root_path)).replace("\\", "/")
                    except ValueError:
                        rel_file = filename
                    score = self._compute_score(query, filename, rel_path=rel_file)

                    if score >= min_score:
                        results.append(
                            SearchResult(
                                path=file_path,
                                name=filename,
                                is_dir=False,
                                size_bytes=file_size,
                                match_score=score,
                                parent_dir=current_path,
                            )
                        )

        # Sort results by score descending (highest quality match first)
        results.sort(key=lambda x: x.match_score, reverse=True)

        if max_results:
            results = results[:max_results]

        return results

    def _compute_score(self, query: str, candidate_name: str, rel_path: Optional[str] = None) -> float:
        """
        Computes match score between query and candidate_name (and optional rel_path).
        Supports:
        - Exact matches (score 100.0)
        - Glob wildcard patterns (*, ?, []) using fnmatch (score 100.0 if matched, 0.0 if not)
        - RapidFuzz WRatio fuzzy matching for natural language / partial queries
        Returns a float between 0.0 and 100.0.
        """
        if not query or query == "*":
            return 100.0  # Wildcard or empty query matches everything with top score

        q_lower = query.lower()
        c_lower = candidate_name.lower()

        normalized_q = q_lower.replace("\\", "/")
        normalized_rel = rel_path.lower().replace("\\", "/") if rel_path else None

        # Check for glob/wildcard patterns (*, ?, [])
        has_wildcard = any(ch in query for ch in ("*", "?", "["))
        if has_wildcard:
            # 1. Direct filename pattern match (e.g. *.png, invoice_*.pdf)
            if fnmatch.fnmatchcase(c_lower, q_lower):
                return 100.0
            # 2. Relative path pattern match if query contains slashes (e.g. docs/*.pdf, src/**/test_*.py)
            if normalized_rel and ("/" in normalized_q):
                if fnmatch.fnmatchcase(normalized_rel, normalized_q):
                    return 100.0
            return 0.0

        # Exact match on filename
        if q_lower == c_lower:
            return 100.0

        # Exact match on relative path
        if normalized_rel and normalized_q == normalized_rel:
            return 100.0

        # Using WRatio (Weighted Ratio) which handles partial matches, case differences,
        # and substring matches intelligently.
        score = float(fuzz.WRatio(q_lower, c_lower))
        if normalized_rel and ("/" in normalized_q):
            rel_score = float(fuzz.WRatio(normalized_q, normalized_rel))
            score = max(score, rel_score)

        return score
