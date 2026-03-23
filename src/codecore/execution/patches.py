"""Patch helpers built on top of workspace file operations."""

from __future__ import annotations

from dataclasses import dataclass

from .files import FileSnapshot, WorkspaceFiles


@dataclass(slots=True, frozen=True)
class PatchApplication:
    path: str
    diff: str
    backup_path: str | None


class PatchService:
    def __init__(self, workspace_files: WorkspaceFiles) -> None:
        self._workspace_files = workspace_files

    def preview_replace(self, relative: str, new_content: str) -> str:
        old_content = self._workspace_files.read_text(relative) or ""
        return self._workspace_files.diff_text(relative, old_content, new_content)

    def replace_text(self, relative: str, needle: str, replacement: str) -> PatchApplication:
        old_content = self._workspace_files.read_text(relative)
        if old_content is None:
            raise FileNotFoundError(relative)
        occurrences = old_content.count(needle)
        if occurrences == 0:
            raise ValueError("needle_not_found")
        if occurrences > 1:
            raise ValueError("needle_ambiguous")
        new_content = old_content.replace(needle, replacement, 1)
        snapshot = self._workspace_files.write_text(relative, new_content)
        return self._to_application(snapshot)

    def replace_file(self, relative: str, new_content: str) -> PatchApplication:
        snapshot = self._workspace_files.write_text(relative, new_content)
        return self._to_application(snapshot)

    def undo(self, relative: str, backup_path: str | None) -> None:
        self._workspace_files.restore_snapshot(relative, backup_path)

    def _to_application(self, snapshot: FileSnapshot) -> PatchApplication:
        return PatchApplication(path=snapshot.path, diff=snapshot.diff, backup_path=snapshot.backup_path)
