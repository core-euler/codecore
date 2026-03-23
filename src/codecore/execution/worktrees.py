"""Git worktree management for isolated execution contexts."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class WorktreeHandle:
    name: str
    path: Path
    head_ref: str
    branch: str | None = None


class WorktreeManager:
    def __init__(self, root: Path, base_dir: Path) -> None:
        self._root = root.resolve()
        self._base_dir = base_dir.resolve()
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def is_supported(self) -> bool:
        return (self._root / ".git").exists() and self._run("rev-parse", "--verify", "HEAD").returncode == 0

    def create(self, name: str, *, ref: str = "HEAD") -> WorktreeHandle:
        if not self.is_supported():
            raise RuntimeError("Git worktrees require a repository with at least one commit.")
        path = self._base_dir / name
        if path.exists():
            raise RuntimeError(f"Worktree path already exists: {path}")
        result = self._run("worktree", "add", "--detach", str(path), ref)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git worktree add failed")
        head = self._run("rev-parse", "HEAD", cwd=path)
        return WorktreeHandle(name=name, path=path, head_ref=head.stdout.strip() or ref)

    def remove(self, handle: WorktreeHandle) -> None:
        result = self._run("worktree", "remove", "--force", str(handle.path))
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git worktree remove failed")

    def list(self) -> tuple[WorktreeHandle, ...]:
        if not self.is_supported():
            return ()
        result = self._run("worktree", "list", "--porcelain")
        if result.returncode != 0:
            return ()
        handles: list[WorktreeHandle] = []
        current_path: Path | None = None
        current_head: str | None = None
        current_branch: str | None = None
        for line in result.stdout.splitlines():
            if not line.strip():
                if current_path is not None and current_head is not None:
                    handles.append(
                        WorktreeHandle(
                            name=current_path.name,
                            path=current_path,
                            head_ref=current_head,
                            branch=current_branch,
                        )
                    )
                current_path = None
                current_head = None
                current_branch = None
                continue
            key, _, value = line.partition(" ")
            if key == "worktree":
                current_path = Path(value).resolve()
            elif key == "HEAD":
                current_head = value
            elif key == "branch":
                current_branch = value.removeprefix("refs/heads/")
        if current_path is not None and current_head is not None:
            handles.append(
                WorktreeHandle(
                    name=current_path.name,
                    path=current_path,
                    head_ref=current_head,
                    branch=current_branch,
                )
            )
        return tuple(handles)

    def _run(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=str(cwd or self._root),
            capture_output=True,
            text=True,
            check=False,
        )
