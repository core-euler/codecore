"""Exact-content change sets for isolated workspace merge flows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .files import WorkspaceFiles
from .patches import PatchApplication, PatchService


@dataclass(slots=True, frozen=True)
class ChangeSetEntry:
    path: str
    before: str
    after: str
    diff: str


@dataclass(slots=True, frozen=True)
class ChangeSet:
    source_workspace: str
    target_workspace: str
    entries: tuple[ChangeSetEntry, ...]

    def paths(self) -> tuple[str, ...]:
        return tuple(item.path for item in self.entries)

    def is_empty(self) -> bool:
        return not self.entries


@dataclass(slots=True, frozen=True)
class ChangeSetApplyResult:
    applied_files: tuple[str, ...]
    diff_summary: str
    conflicts: tuple[str, ...] = ()
    applications: tuple[PatchApplication, ...] = ()


class ChangeSetBuilder:
    def __init__(self, base_root: Path, updated_root: Path, artifact_dir: Path) -> None:
        self._base_root = base_root.resolve()
        self._updated_root = updated_root.resolve()
        self._base_files = WorkspaceFiles(self._base_root, artifact_dir / "changeset-base")
        self._updated_files = WorkspaceFiles(self._updated_root, artifact_dir / "changeset-updated")

    def build(self, paths: tuple[str, ...]) -> ChangeSet:
        entries: list[ChangeSetEntry] = []
        for path in paths:
            before = self._base_files.read_text(path) or ""
            after_text = self._updated_files.read_text(path)
            if after_text is None:
                continue
            if before == after_text:
                continue
            diff = self._base_files.diff_text(path, before, after_text)
            entries.append(ChangeSetEntry(path=path, before=before, after=after_text, diff=diff))
        return ChangeSet(
            source_workspace=str(self._updated_root),
            target_workspace=str(self._base_root),
            entries=tuple(entries),
        )


class ChangeSetApplier:
    def __init__(self, patch_service: PatchService) -> None:
        self._patch_service = patch_service
        self._workspace_files = patch_service.workspace_files

    def apply(self, change_set: ChangeSet) -> ChangeSetApplyResult:
        if change_set.is_empty():
            return ChangeSetApplyResult(applied_files=(), diff_summary="No change-set entries to apply.")

        conflicts: list[str] = []
        for entry in change_set.entries:
            current = self._workspace_files.read_text(entry.path) or ""
            if current != entry.before:
                conflicts.append(entry.path)
        if conflicts:
            return ChangeSetApplyResult(
                applied_files=(),
                conflicts=tuple(conflicts),
                diff_summary="Conflicts detected for: " + ", ".join(conflicts),
            )

        applied: list[PatchApplication] = []
        backups: list[tuple[str, str | None]] = []
        try:
            for entry in change_set.entries:
                application = self._patch_service.replace_file(entry.path, entry.after)
                applied.append(application)
                backups.append((entry.path, application.backup_path))
        except Exception as exc:
            for path, backup_path in reversed(backups):
                self._patch_service.undo(path, backup_path)
            raise RuntimeError(f"Failed to apply change set: {exc}") from exc

        diff_blocks = [item.diff for item in applied if item.diff.strip()]
        return ChangeSetApplyResult(
            applied_files=tuple(item.path for item in applied),
            applications=tuple(applied),
            diff_summary="\n\n".join(diff_blocks) or "No changes applied.",
        )
