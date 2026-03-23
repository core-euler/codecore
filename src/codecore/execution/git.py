"""Git-backed diff and restore helpers."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class GitCommandResult:
    exit_code: int
    stdout: str
    stderr: str = ""


class GitWorkspace:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def is_repository(self) -> bool:
        return (self._root / ".git").exists()

    def has_head(self) -> bool:
        result = self._run("rev-parse", "--verify", "HEAD")
        return result.exit_code == 0

    def diff_summary(self, paths: tuple[str, ...] = ()) -> str:
        if not self.is_repository():
            return "Git repository is not initialized."
        status = self._run("status", "--short", "--untracked-files=all")
        diff_args = ["diff", "--no-ext-diff"]
        if paths:
            diff_args.extend(["--", *paths])
        diff = self._run(*diff_args)
        parts: list[str] = []
        if status.stdout.strip():
            parts.append("status:\n" + status.stdout.strip())
        if diff.stdout.strip():
            parts.append("diff:\n" + diff.stdout.strip())
        if not parts:
            return "Working tree is clean."
        return "\n\n".join(parts)

    def restore(self, paths: tuple[str, ...] = ()) -> str:
        if not self.is_repository():
            return "Git repository is not initialized."
        if not self.has_head():
            return "Undo is unavailable until the repository has at least one commit."
        changed = self.changed_files()
        if not changed:
            return "Working tree is already clean."
        target_paths = tuple(path for path in (paths or changed) if path in changed)
        if not target_paths:
            return "No tracked changed files matched the undo target set."
        tracked = [path for path in target_paths if path not in self.untracked_files()]
        skipped = [path for path in target_paths if path in self.untracked_files()]
        messages: list[str] = []
        if tracked:
            result = self._run("restore", "--source=HEAD", "--worktree", "--staged", "--", *tracked)
            if result.exit_code != 0:
                return result.stderr.strip() or result.stdout.strip() or "git restore failed."
            messages.append("Restored tracked files: " + ", ".join(tracked))
        if skipped:
            messages.append("Skipped untracked files: " + ", ".join(skipped))
        return "\n".join(messages)

    def changed_files(self) -> tuple[str, ...]:
        if not self.is_repository():
            return ()
        status = self._run("status", "--short", "--untracked-files=all")
        files: list[str] = []
        for line in status.stdout.splitlines():
            if not line.strip():
                continue
            files.append(line[3:].strip())
        return tuple(files)

    def untracked_files(self) -> tuple[str, ...]:
        if not self.is_repository():
            return ()
        status = self._run("status", "--short", "--untracked-files=all")
        return tuple(line[3:].strip() for line in status.stdout.splitlines() if line.startswith("?? "))

    def _run(self, *args: str) -> GitCommandResult:
        proc = subprocess.run(
            ["git", *args],
            cwd=self._root,
            capture_output=True,
            text=True,
            check=False,
        )
        return GitCommandResult(exit_code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
