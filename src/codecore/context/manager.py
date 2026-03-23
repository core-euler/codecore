"""Track active files and produce prompt-ready snippets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..governance.security import guard_untrusted_content
from .token_budget import estimate_text_tokens

_SYMBOL_PATTERNS = (
    re.compile(r"^\s*(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"^\s*(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*="),
)


@dataclass(slots=True, frozen=True)
class FileContextStats:
    path: str
    size_bytes: int
    line_count: int
    token_estimate: int
    is_large: bool
    headings: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()


class ContextManager:
    def __init__(self, project_root: Path, max_file_bytes: int = 12000, summary_trigger_tokens: int = 1600) -> None:
        self._project_root = project_root.resolve()
        self._max_file_bytes = max_file_bytes
        self._summary_trigger_tokens = summary_trigger_tokens

    def normalize_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if not path.is_absolute():
            path = (self._project_root / path).resolve()
        return path

    @property
    def project_root(self) -> Path:
        return self._project_root

    def add_files(self, current: list[str], raw_paths: list[str]) -> tuple[list[str], list[str]]:
        added: list[str] = []
        for raw_path in raw_paths:
            path = self.normalize_path(raw_path)
            if not path.exists() or not path.is_file():
                continue
            try:
                relative = str(path.relative_to(self._project_root))
            except ValueError:
                continue
            if relative not in current:
                current.append(relative)
                added.append(relative)
        return current, added

    def drop_files(self, current: list[str], raw_paths: list[str]) -> tuple[list[str], list[str]]:
        removed: list[str] = []
        normalized: set[str] = set()
        for raw_path in raw_paths:
            try:
                normalized.add(str(self.normalize_path(raw_path).relative_to(self._project_root)))
            except ValueError:
                continue
        for path in list(current):
            if path in normalized:
                current.remove(path)
                removed.append(path)
        return current, removed

    def resolve_relative(self, relative: str) -> Path:
        return (self._project_root / relative).resolve()

    def read_text(self, relative: str, *, truncate: bool = True) -> str | None:
        path = self.resolve_relative(relative)
        if not path.exists() or not path.is_file():
            return None
        content = path.read_text(encoding="utf-8", errors="replace")
        if truncate and len(content.encode("utf-8")) > self._max_file_bytes:
            content = content[: self._max_file_bytes] + "\n...<truncated>"
        return content

    def describe_file(self, relative: str) -> FileContextStats | None:
        content = self.read_text(relative, truncate=False)
        if content is None:
            return None
        encoded = content.encode("utf-8")
        lines = content.splitlines()
        line_count = len(lines) if lines else (1 if content else 0)
        token_estimate = estimate_text_tokens(content)
        return FileContextStats(
            path=relative,
            size_bytes=len(encoded),
            line_count=line_count,
            token_estimate=token_estimate,
            is_large=len(encoded) > self._max_file_bytes or token_estimate > self._summary_trigger_tokens,
            headings=self._extract_headings(lines),
            symbols=self._extract_symbols(lines),
        )

    def describe_active_files(self, paths: list[str]) -> tuple[FileContextStats, ...]:
        stats: list[FileContextStats] = []
        for relative in paths:
            item = self.describe_file(relative)
            if item is not None:
                stats.append(item)
        return tuple(stats)

    def summarize_file(self, relative: str, *, head_lines: int = 6, tail_lines: int = 4) -> str | None:
        content = self.read_text(relative, truncate=False)
        stats = self.describe_file(relative)
        if content is None or stats is None:
            return None

        lines = content.splitlines()
        head_preview = "\n".join(lines[:head_lines]).strip()
        tail_preview = "\n".join(lines[-tail_lines:]).strip() if len(lines) > head_lines else ""

        parts = [
            f"Path: {stats.path}",
            f"Bytes: {stats.size_bytes}",
            f"Lines: {stats.line_count}",
            f"Estimated tokens: {stats.token_estimate}",
        ]
        if stats.headings:
            parts.append("Headings: " + ", ".join(stats.headings))
        if stats.symbols:
            parts.append("Symbols: " + ", ".join(stats.symbols))
        if head_preview:
            parts.append("Head preview:\n" + head_preview)
        if tail_preview and tail_preview != head_preview:
            parts.append("Tail preview:\n" + tail_preview)
        return "\n\n".join(parts)

    def render_file_context(self, paths: list[str]) -> str:
        blocks: list[str] = []
        for relative in paths:
            content = self.read_text(relative)
            if content is None:
                continue
            guarded = guard_untrusted_content(f"file:{relative}", content)
            blocks.append(f"FILE: {relative}\n```\n{guarded.rendered}\n```")
        return "\n\n".join(blocks)

    def _extract_headings(self, lines: list[str], limit: int = 6) -> tuple[str, ...]:
        headings: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith("#"):
                continue
            heading = stripped.lstrip("#").strip()
            if heading:
                headings.append(heading[:80])
            if len(headings) >= limit:
                break
        return tuple(headings)

    def _extract_symbols(self, lines: list[str], limit: int = 8) -> tuple[str, ...]:
        symbols: list[str] = []
        for line in lines:
            for pattern in _SYMBOL_PATTERNS:
                match = pattern.match(line)
                if not match:
                    continue
                symbols.append(match.group(1))
                break
            if len(symbols) >= limit:
                break
        return tuple(symbols)
