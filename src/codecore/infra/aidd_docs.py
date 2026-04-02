"""Markdown-backed AIDD issue and antipattern tracking."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


_ENTRY_RE = re.compile(r"^## \[(?P<entry_id>[A-Z]+-\d+)\] (?P<title>.+)$", re.MULTILINE)
_FIELD_RE = re.compile(r"^\*\*(?P<name>[^*]+):\*\*\s*$", re.MULTILINE)


@dataclass(slots=True, frozen=True)
class IssueEntry:
    entry_id: str
    title: str
    status: str
    description: str
    cause: str
    resolution: str
    spec_changes: str


@dataclass(slots=True, frozen=True)
class AntipatternEntry:
    entry_id: str
    title: str
    traceback: str
    cause: str
    resolution: str


class AIDDDocsStore:
    def __init__(self, project_root: Path) -> None:
        self._docs_dir = project_root / "docs"
        self._issues_path = self._docs_dir / "issues.md"
        self._antipatterns_path = self._docs_dir / "antipatterns.md"
        self._docs_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_file(self._issues_path, "# Issues\n\n")
        self._ensure_file(self._antipatterns_path, "# Antipatterns\n\n")

    @property
    def issues_path(self) -> Path:
        return self._issues_path

    @property
    def antipatterns_path(self) -> Path:
        return self._antipatterns_path

    def add_issue(self, description: str) -> IssueEntry:
        entry_id = self._next_id(self._issues_path, "ISSUE")
        title = self._title_from_text(description)
        entry = IssueEntry(
            entry_id=entry_id,
            title=title,
            status="Open",
            description=description.strip(),
            cause="TBD",
            resolution="TBD",
            spec_changes="None",
        )
        self._append_entry(self._issues_path, self._render_issue(entry))
        return entry

    def list_issues(self, *, include_closed: bool = False) -> tuple[IssueEntry, ...]:
        entries = self._parse_issues()
        if include_closed:
            return entries
        return tuple(item for item in entries if item.status.lower() != "closed" and item.status.lower() != "resolved")

    def close_issue(self, entry_id: str, resolution: str | None = None) -> IssueEntry | None:
        entries = list(self._parse_issues())
        updated: IssueEntry | None = None
        for index, item in enumerate(entries):
            if item.entry_id != entry_id:
                continue
            updated = IssueEntry(
                entry_id=item.entry_id,
                title=item.title,
                status="Resolved",
                description=item.description,
                cause=item.cause,
                resolution=(resolution or item.resolution or "Resolved via /issue close").strip(),
                spec_changes=item.spec_changes,
            )
            entries[index] = updated
            break
        if updated is None:
            return None
        self._rewrite_issues(entries)
        return updated

    def add_antipattern(self, details: str) -> AntipatternEntry:
        entry_id = self._next_id(self._antipatterns_path, "AP")
        title = self._title_from_text(details)
        entry = AntipatternEntry(
            entry_id=entry_id,
            title=title,
            traceback=details.strip(),
            cause="TBD",
            resolution="TBD",
        )
        self._append_entry(self._antipatterns_path, self._render_antipattern(entry))
        return entry

    def list_antipatterns(self) -> tuple[AntipatternEntry, ...]:
        return self._parse_antipatterns()

    def search_antipatterns(self, query: str) -> tuple[AntipatternEntry, ...]:
        needle = query.lower().strip()
        if not needle:
            return ()
        return tuple(
            item
            for item in self._parse_antipatterns()
            if needle in item.title.lower()
            or needle in item.traceback.lower()
            or needle in item.cause.lower()
            or needle in item.resolution.lower()
        )

    def _parse_issues(self) -> tuple[IssueEntry, ...]:
        text = self._issues_path.read_text(encoding="utf-8")
        sections = self._split_entries(text)
        entries: list[IssueEntry] = []
        for entry_id, title, body in sections:
            fields = self._parse_fields(body)
            entries.append(
                IssueEntry(
                    entry_id=entry_id,
                    title=title,
                    status=fields.get("Status", "Open"),
                    description=fields.get("Description", ""),
                    cause=fields.get("Cause", ""),
                    resolution=fields.get("Resolution", ""),
                    spec_changes=fields.get("Spec Changes", ""),
                )
            )
        return tuple(entries)

    def _parse_antipatterns(self) -> tuple[AntipatternEntry, ...]:
        text = self._antipatterns_path.read_text(encoding="utf-8")
        sections = self._split_entries(text)
        entries: list[AntipatternEntry] = []
        for entry_id, title, body in sections:
            fields = self._parse_fields(body)
            entries.append(
                AntipatternEntry(
                    entry_id=entry_id,
                    title=title,
                    traceback=fields.get("Traceback", ""),
                    cause=fields.get("Cause", ""),
                    resolution=fields.get("Resolution", ""),
                )
            )
        return tuple(entries)

    def _rewrite_issues(self, entries: list[IssueEntry]) -> None:
        content = "# Issues\n\n"
        if entries:
            content += "\n\n".join(self._render_issue(entry).strip() for entry in entries) + "\n"
        self._issues_path.write_text(content, encoding="utf-8")

    @staticmethod
    def _ensure_file(path: Path, initial_text: str) -> None:
        if not path.exists():
            path.write_text(initial_text, encoding="utf-8")

    @staticmethod
    def _title_from_text(text: str, *, max_len: int = 72) -> str:
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), "Entry")
        return first_line[:max_len]

    @staticmethod
    def _append_entry(path: Path, block: str) -> None:
        base = path.read_text(encoding="utf-8").rstrip()
        if not base:
            path.write_text(block.strip() + "\n", encoding="utf-8")
            return
        path.write_text(base + "\n\n" + block.strip() + "\n", encoding="utf-8")

    @staticmethod
    def _next_id(path: Path, prefix: str) -> str:
        text = path.read_text(encoding="utf-8")
        numbers = [int(match.group(1)) for match in re.finditer(rf"\[{prefix}-(\d+)\]", text)]
        next_number = (max(numbers) + 1) if numbers else 1
        return f"{prefix}-{next_number:03d}"

    @staticmethod
    def _render_issue(entry: IssueEntry) -> str:
        return (
            f"## [{entry.entry_id}] {entry.title}\n\n"
            f"**Status:**\n{entry.status}\n\n"
            f"**Description:**\n{entry.description}\n\n"
            f"**Cause:**\n{entry.cause}\n\n"
            f"**Resolution:**\n{entry.resolution}\n\n"
            f"**Spec Changes:**\n{entry.spec_changes}\n"
        )

    @staticmethod
    def _render_antipattern(entry: AntipatternEntry) -> str:
        return (
            f"## [{entry.entry_id}] {entry.title}\n\n"
            f"**Traceback:**\n{entry.traceback}\n\n"
            f"**Cause:**\n{entry.cause}\n\n"
            f"**Resolution:**\n{entry.resolution}\n"
        )

    @staticmethod
    def _split_entries(text: str) -> tuple[tuple[str, str, str], ...]:
        matches = list(_ENTRY_RE.finditer(text))
        sections: list[tuple[str, str, str]] = []
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            sections.append((match.group("entry_id"), match.group("title").strip(), text[start:end].strip()))
        return tuple(sections)

    @staticmethod
    def _parse_fields(body: str) -> dict[str, str]:
        matches = list(_FIELD_RE.finditer(body))
        fields: dict[str, str] = {}
        for index, match in enumerate(matches):
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
            fields[match.group("name").strip()] = body[start:end].strip()
        return fields
