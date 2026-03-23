"""Native repository-inspection tools for conversational turns."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..context.manager import ContextManager
from ..context.repo_map import RepoMapBuilder
from ..domain.enums import ToolKind
from ..domain.results import ToolExecutionResult
from .shell import summarize_output

_IGNORED_DIRS = {
    ".git",
    ".codecore",
    ".codecore-home",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
}


@dataclass(slots=True, frozen=True)
class NativeToolCall:
    tool: str
    args: dict[str, object]
    message: str = ""


class NativeRepositoryTools:
    def __init__(self, context_manager: ContextManager, repo_map_builder: RepoMapBuilder | None = None) -> None:
        self._context_manager = context_manager
        self._repo_map_builder = repo_map_builder or RepoMapBuilder(context_manager.project_root)

    def execute(self, call: NativeToolCall) -> ToolExecutionResult:
        tool = call.tool.strip().lower()
        if tool == "read":
            return self._read(call.args)
        if tool == "search":
            return self._search(call.args)
        if tool == "list":
            return self._list(call.args)
        if tool == "repo_map":
            return self._repo_map(call.args)
        return ToolExecutionResult(
            tool_kind=ToolKind.FILESYSTEM,
            command=f"{tool}",
            exit_code=1,
            stderr=f"Unknown native tool: {tool}",
            metadata={"tool": tool},
        )

    def _read(self, args: dict[str, object]) -> ToolExecutionResult:
        raw_path = str(args.get("path", "")).strip()
        if not raw_path:
            return self._error("read", "Argument 'path' is required.")
        try:
            relative = self._relative_path(raw_path)
        except ValueError as exc:
            return self._error("read", str(exc), path=raw_path)
        content = self._context_manager.read_text(relative, truncate=False)
        if content is None:
            return self._error("read", f"File not found: {relative}", path=relative)
        lines = content.splitlines()
        start_line = self._coerce_int(args.get("start_line"), default=1, minimum=1)
        end_line = self._coerce_int(args.get("end_line"), default=min(len(lines) or 1, start_line + 199), minimum=start_line)
        selected = lines[start_line - 1 : end_line]
        numbered = "\n".join(f"{index}: {line}" for index, line in enumerate(selected, start=start_line))
        rendered = f"READ {relative} [{start_line}-{end_line}]\n{numbered}".strip()
        return ToolExecutionResult(
            tool_kind=ToolKind.FILESYSTEM,
            command=f"read {relative}",
            exit_code=0,
            stdout=summarize_output(rendered, max_chars=4000).rendered,
            affected_files=(relative,),
            metadata={"tool": "read", "path": relative, "start_line": start_line, "end_line": end_line},
        )

    def _search(self, args: dict[str, object]) -> ToolExecutionResult:
        query = str(args.get("query", "")).strip()
        raw_path = str(args.get("path", ".")).strip() or "."
        if not query:
            return self._error("search", "Argument 'query' is required.")
        max_matches = self._coerce_int(args.get("max_matches"), default=20, minimum=1)
        start_path = self._resolve_start_path(raw_path)
        if start_path is None:
            return self._error("search", f"Path not found: {raw_path}", path=raw_path)
        lowered = query.lower()
        matches: list[str] = []
        touched: list[str] = []
        for file_path in self._iter_files(start_path):
            relative = str(file_path.relative_to(self._context_manager.project_root))
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                if lowered not in line.lower():
                    continue
                snippet = line.strip()
                matches.append(f"{relative}:{line_number}: {snippet}")
                if relative not in touched:
                    touched.append(relative)
                if len(matches) >= max_matches:
                    rendered = "\n".join(matches)
                    return ToolExecutionResult(
                        tool_kind=ToolKind.FILESYSTEM,
                        command=f"search {query}",
                        exit_code=0,
                        stdout=rendered,
                        affected_files=tuple(touched),
                        metadata={"tool": "search", "query": query, "path": raw_path, "match_count": len(matches)},
                    )
        rendered = "\n".join(matches) if matches else f"No matches for '{query}'."
        return ToolExecutionResult(
            tool_kind=ToolKind.FILESYSTEM,
            command=f"search {query}",
            exit_code=0,
            stdout=rendered,
            affected_files=tuple(touched),
            metadata={"tool": "search", "query": query, "path": raw_path, "match_count": len(matches)},
        )

    def _list(self, args: dict[str, object]) -> ToolExecutionResult:
        raw_path = str(args.get("path", ".")).strip() or "."
        max_entries = self._coerce_int(args.get("max_entries"), default=80, minimum=1)
        start_path = self._resolve_start_path(raw_path)
        if start_path is None:
            return self._error("list", f"Path not found: {raw_path}", path=raw_path)
        entries: list[str] = []
        for file_path in self._iter_files(start_path):
            entries.append(str(file_path.relative_to(self._context_manager.project_root)))
            if len(entries) >= max_entries:
                break
        rendered = "\n".join(entries) if entries else "<no files>"
        return ToolExecutionResult(
            tool_kind=ToolKind.FILESYSTEM,
            command=f"list {raw_path}",
            exit_code=0,
            stdout=rendered,
            affected_files=tuple(entries),
            metadata={"tool": "list", "path": raw_path, "entry_count": len(entries)},
        )

    def _repo_map(self, args: dict[str, object]) -> ToolExecutionResult:
        max_depth = self._coerce_int(args.get("max_depth"), default=4, minimum=1)
        rendered = self._repo_map_builder.build_for_budget(800, max_depth=max_depth)
        return ToolExecutionResult(
            tool_kind=ToolKind.FILESYSTEM,
            command="repo_map",
            exit_code=0,
            stdout=rendered,
            metadata={"tool": "repo_map", "max_depth": max_depth},
        )

    def _error(self, tool: str, message: str, *, path: str | None = None) -> ToolExecutionResult:
        metadata: dict[str, object] = {"tool": tool}
        if path is not None:
            metadata["path"] = path
        return ToolExecutionResult(
            tool_kind=ToolKind.FILESYSTEM,
            command=tool,
            exit_code=1,
            stderr=message,
            metadata=metadata,
        )

    def _relative_path(self, raw_path: str) -> str:
        path = self._context_manager.normalize_path(raw_path)
        try:
            return str(path.relative_to(self._context_manager.project_root))
        except ValueError as exc:
            raise ValueError(f"Path escapes the project root: {raw_path}") from exc

    def _resolve_start_path(self, raw_path: str) -> Path | None:
        path = self._context_manager.normalize_path(raw_path)
        if not path.exists():
            return None
        return path

    def _iter_files(self, start_path: Path):
        if start_path.is_file():
            yield start_path
            return
        stack = [start_path]
        while stack:
            current = stack.pop()
            try:
                children = sorted(current.iterdir(), key=lambda item: (item.is_file(), item.name))
            except OSError:
                continue
            for child in reversed(children):
                if child.name in _IGNORED_DIRS:
                    continue
                if child.is_dir():
                    stack.append(child)
                    continue
                yield child

    @staticmethod
    def _coerce_int(value: object, *, default: int, minimum: int) -> int:
        if value is None:
            return default
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        return max(minimum, parsed)
