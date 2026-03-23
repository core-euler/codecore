"""Shell execution with summary-first output shaping."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

from ..domain.contracts import ToolExecutor
from ..domain.enums import ToolKind
from ..domain.results import ToolExecutionResult


@dataclass(slots=True, frozen=True)
class OutputSummary:
    rendered: str
    truncated: bool
    original_chars: int


class ShellToolExecutor(ToolExecutor):
    def __init__(self, *, shell: str = "/bin/zsh", max_output_chars: int = 2000) -> None:
        self._shell = shell
        self._max_output_chars = max_output_chars

    async def run_shell(self, command: str, *, cwd: Path | None = None) -> ToolExecutionResult:
        started = time.perf_counter()
        process = await asyncio.create_subprocess_exec(
            self._shell,
            "-lc",
            command,
            cwd=str(cwd) if cwd is not None else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await process.communicate()
        duration_ms = int((time.perf_counter() - started) * 1000)
        stdout_text = stdout_bytes.decode("utf-8", errors="replace")
        stderr_text = stderr_bytes.decode("utf-8", errors="replace")
        stdout_summary = summarize_output(stdout_text, max_chars=self._max_output_chars)
        stderr_summary = summarize_output(stderr_text, max_chars=self._max_output_chars)
        return ToolExecutionResult(
            tool_kind=ToolKind.SHELL,
            command=command,
            exit_code=process.returncode,
            stdout=stdout_summary.rendered,
            stderr=stderr_summary.rendered,
            duration_ms=duration_ms,
            metadata={
                "stdout_original_chars": stdout_summary.original_chars,
                "stderr_original_chars": stderr_summary.original_chars,
                "stdout_truncated": stdout_summary.truncated,
                "stderr_truncated": stderr_summary.truncated,
            },
        )


def summarize_output(text: str, *, max_chars: int = 2000, head_lines: int = 16, tail_lines: int = 10) -> OutputSummary:
    if len(text) <= max_chars:
        return OutputSummary(rendered=text.strip(), truncated=False, original_chars=len(text))
    lines = text.splitlines()
    head = "\n".join(lines[:head_lines]).strip()
    tail = "\n".join(lines[-tail_lines:]).strip()
    omitted_lines = max(0, len(lines) - head_lines - tail_lines)
    rendered = (
        f"{head}\n"
        f"... <omitted {omitted_lines} lines / {len(text)} chars> ...\n"
        f"{tail}"
    ).strip()
    return OutputSummary(rendered=rendered, truncated=True, original_chars=len(text))
