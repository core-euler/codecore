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


@dataclass(slots=True, frozen=True)
class FileChangeStat:
    path: str
    status: str
    added: int
    removed: int


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

    def change_stats(self, paths: tuple[str, ...] = ()) -> tuple[FileChangeStat, ...]:
        if not self.is_repository():
            return ()
        status_result = self._run("status", "--short", "--untracked-files=all")
        status_map: dict[str, str] = {}
        for line in status_result.stdout.splitlines():
            if not line.strip():
                continue
            code = line[:2]
            path = line[3:].strip()
            if paths and path not in paths:
                continue
            status_map[path] = self._normalize_status(code)

        numstats: dict[str, tuple[int, int]] = {}
        for args in (("diff", "--numstat", "--no-ext-diff"), ("diff", "--cached", "--numstat", "--no-ext-diff")):
            result = self._run(*args)
            for line in result.stdout.splitlines():
                parts = line.split("\t")
                if len(parts) != 3:
                    continue
                added_text, removed_text, path = parts
                if paths and path not in paths:
                    continue
                added = 0 if added_text == "-" else int(added_text)
                removed = 0 if removed_text == "-" else int(removed_text)
                prev_added, prev_removed = numstats.get(path, (0, 0))
                numstats[path] = (prev_added + added, prev_removed + removed)

        stats: list[FileChangeStat] = []
        for path in sorted(status_map):
            added, removed = numstats.get(path, (0, 0))
            stats.append(FileChangeStat(path=path, status=status_map[path], added=added, removed=removed))
        return tuple(stats)

    @staticmethod
    def _normalize_status(code: str) -> str:
        stripped = code.strip()
        if stripped == "??":
            return "untracked"
        if "R" in code:
            return "renamed"
        if "D" in code:
            return "deleted"
        if "A" in code:
            return "added"
        if "M" in code:
            return "modified"
        return stripped.lower() or "changed"

    def _run(self, *args: str) -> GitCommandResult:
        proc = subprocess.run(
            ["git", *args],
            cwd=self._root,
            capture_output=True,
            text=True,
            check=False,
        )
        return GitCommandResult(exit_code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
