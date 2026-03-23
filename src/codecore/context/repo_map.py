"""Compact repository map builder for prompt context."""

from __future__ import annotations

from pathlib import Path

from .token_budget import estimate_text_tokens


class RepoMapBuilder:
    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root.resolve()
        self._ignored_dirs = {
            ".git",
            ".venv",
            "__pycache__",
            ".codecore-home",
            "dist",
            "build",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
        }
        self._ignored_files = {".DS_Store"}

    def build(self, *, max_depth: int = 2, max_entries: int = 48) -> str:
        lines: list[str] = []
        self._walk(self._project_root, depth=0, max_depth=max_depth, max_entries=max_entries, lines=lines)
        return "\n".join(lines)

    def build_for_budget(self, budget_tokens: int, *, max_depth: int = 2) -> str:
        if budget_tokens <= 0:
            return ""
        max_entries = max(8, min(64, budget_tokens // 8))
        text = self.build(max_depth=max_depth, max_entries=max_entries)
        if estimate_text_tokens(text) > budget_tokens:
            text = self.build(max_depth=1, max_entries=max(8, max_entries // 2))
        return text if estimate_text_tokens(text) <= budget_tokens else ""

    def _walk(self, path: Path, *, depth: int, max_depth: int, max_entries: int, lines: list[str]) -> None:
        if len(lines) >= max_entries or depth > max_depth:
            return
        entries = sorted(
            (
                entry
                for entry in path.iterdir()
                if not self._skip(entry)
            ),
            key=lambda entry: (entry.is_file(), entry.name.lower()),
        )
        for entry in entries:
            if len(lines) >= max_entries:
                lines.append("  " * depth + "...")
                return
            marker = "/" if entry.is_dir() else ""
            lines.append(f"{'  ' * depth}{entry.name}{marker}")
            if entry.is_dir():
                self._walk(entry, depth=depth + 1, max_depth=max_depth, max_entries=max_entries, lines=lines)

    def _skip(self, entry: Path) -> bool:
        name = entry.name
        if name in self._ignored_files:
            return True
        if entry.is_dir() and name in self._ignored_dirs:
            return True
        return False
