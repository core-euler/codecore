"""Interactive terminal REPL."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console

from ..kernel.orchestrator import Orchestrator
from .statusbar import build_status_line


@dataclass(slots=True)
class Repl:
    orchestrator: Orchestrator
    console: Console
    history_path: str | None = None

    async def run(self) -> int:
        await self.orchestrator.start()
        try:
            if sys.stdin.isatty():
                return await self._run_interactive()
            return await self._run_stream()
        finally:
            await self.orchestrator.stop()

    async def _run_interactive(self) -> int:
        history = FileHistory(self.history_path) if self.history_path else None
        prompt = PromptSession(history=history)
        while True:
            self.console.print(build_status_line(self.orchestrator.session, self.orchestrator.runtime_state), style="dim")
            try:
                line = await prompt.prompt_async("> ")
            except KeyboardInterrupt:
                self.console.print("^C", style="yellow")
                continue
            except EOFError:
                self.console.print()
                return 0
            result = await self.orchestrator.handle_line(line)
            if result.output:
                self.console.print(result.output, style="red" if result.is_error else None, markup=False, highlight=False)
            if result.should_exit:
                return 0

    async def _run_stream(self) -> int:
        for raw_line in sys.stdin:
            line = raw_line.rstrip("\n")
            result = await self.orchestrator.handle_line(line)
            if result.output:
                self.console.print(result.output, style="red" if result.is_error else None, markup=False, highlight=False)
            if result.should_exit:
                break
            await asyncio.sleep(0)
        return 0
