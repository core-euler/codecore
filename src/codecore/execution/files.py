"""Workspace-safe file operations with snapshot support."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True, frozen=True)
class FileSnapshot:
    path: str
    backup_path: str | None
    existed_before: bool
    diff: str


class WorkspaceFiles:
    def __init__(self, root: Path, artifact_dir: Path) -> None:
        self._root = root.resolve()
        self._artifact_dir = artifact_dir.resolve()
        self._snapshot_dir = self._artifact_dir / "snapshots"
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)

    def read_text(self, relative: str) -> str | None:
        path = self.resolve(relative)
        if not path.exists() or not path.is_file():
            return None
        return path.read_text(encoding="utf-8", errors="replace")

    def write_text(self, relative: str, content: str) -> FileSnapshot:
        path = self.resolve(relative)
        old_content = self.read_text(relative)
        existed_before = old_content is not None
        backup_path = None
        if existed_before and old_content is not None:
            backup_path = self._write_backup(relative, old_content)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        diff = self.diff_text(relative, old_content or "", content)
        return FileSnapshot(path=relative, backup_path=backup_path, existed_before=existed_before, diff=diff)

    def diff_text(self, relative: str, old_content: str, new_content: str) -> str:
        diff = difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            fromfile=f"a/{relative}",
            tofile=f"b/{relative}",
            lineterm="",
        )
        return "\n".join(diff)

    def restore_snapshot(self, relative: str, backup_path: str | None) -> None:
        path = self.resolve(relative)
        if backup_path is None:
            if path.exists():
                path.unlink()
            return
        backup = Path(backup_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")

    def resolve(self, relative: str) -> Path:
        path = (self._root / relative).resolve()
        if self._root != path and self._root not in path.parents:
            raise ValueError(f"Path escapes workspace root: {relative}")
        return path

    def _write_backup(self, relative: str, content: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_name = relative.replace("/", "__")
        backup = self._snapshot_dir / f"{timestamp}__{safe_name}.bak"
        backup.write_text(content, encoding="utf-8")
        return str(backup)
