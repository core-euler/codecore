"""Interactive terminal REPL."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.markdown import Markdown

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
        key_bindings = KeyBindings()

        @key_bindings.add("c-j")
        def _insert_newline(event) -> None:
            event.current_buffer.insert_text("\n")

        @key_bindings.add("enter")
        def _submit(event) -> None:
            event.current_buffer.validate_and_handle()

        prompt = PromptSession(history=history, multiline=True, key_bindings=key_bindings)
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
            with self.console.status(self._status_text_for(line), spinner="dots"):
                result = await self.orchestrator.handle_line(line)
            if result.output:
                self._render_output(result)
            if result.should_exit:
                return 0

    async def _run_stream(self) -> int:
        for raw_line in sys.stdin:
            line = raw_line.rstrip("\n")
            result = await self.orchestrator.handle_line(line)
            if result.output:
                self._render_output(result)
            if result.should_exit:
                break
            await asyncio.sleep(0)
        return 0

    def _render_output(self, result) -> None:
        if result.render_mode == "markdown" and not result.is_error:
            self.console.print(Markdown(result.output))
            return
        self.console.print(result.output, style="red" if result.is_error else None, markup=False, highlight=False)

    @staticmethod
    def _status_text_for(line: str) -> str:
        stripped = line.strip()
        if not stripped:
            return "ready"
        if not stripped.startswith("/"):
            return "casting spells"
        command = stripped.split(maxsplit=1)[0]
        return {
            "/run": "running tool",
            "/verify": "verifying changes",
            "/autoedit": "planning edits",
            "/delegate": "delegating agents",
            "/benchmark": "benchmarking models",
            "/approve": "applying approval",
        }.get(command, "working")
