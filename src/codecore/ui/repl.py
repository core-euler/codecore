"""Interactive terminal REPL."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts.prompt import CompleteStyle
from rich.align import Align
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from ..kernel.orchestrator import Orchestrator
from .commands import COMMAND_SPECS
from .statusbar import build_status_line


class SlashCommandCompleter(Completer):
    def get_completions(self, document, complete_event):
        text_before_cursor = document.text_before_cursor
        lines = text_before_cursor.splitlines() or [""]
        current_line = lines[-1].lstrip()
        if not current_line.startswith("/"):
            return
        if " " in current_line:
            return
        typed = current_line[1:]
        for spec in COMMAND_SPECS:
            if typed and not spec.name.startswith(typed):
                continue
            yield Completion(
                text=spec.name,
                start_position=-len(typed),
                display=f"/{spec.name}",
                display_meta=spec.description,
            )


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

        prompt = PromptSession(
            history=history,
            multiline=True,
            key_bindings=key_bindings,
            completer=SlashCommandCompleter(),
            complete_while_typing=True,
            complete_style=CompleteStyle.MULTI_COLUMN,
            reserve_space_for_menu=8,
        )
        while True:
            self.console.print()
            self.console.print(build_status_line(self.orchestrator.session, self.orchestrator.runtime_state), style="dim")
            self.console.print()
            try:
                line = await prompt.prompt_async("> ")
            except KeyboardInterrupt:
                self.console.print("^C", style="yellow")
                continue
            except EOFError:
                self.console.print()
                return 0
            self._render_user_input(line)
            with self.console.status(self._status_text_for(line), spinner="dots"):
                result = await self.orchestrator.handle_line(line)
            if result.output:
                self._render_output(result)
            self._render_quick_actions()
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
            panel = Panel(
                Markdown(result.output),
                title="CodeCore",
                border_style="cyan",
                expand=False,
                padding=(0, 1),
            )
            self.console.print(Align.left(panel))
            self.console.print()
            return
        self.console.print(result.output, style="red" if result.is_error else None, markup=False, highlight=False)
        self.console.print()

    def _render_user_input(self, line: str) -> None:
        stripped = line.strip()
        if not stripped or stripped.startswith("/"):
            return
        panel = Panel(
            Text(stripped),
            title="You",
            border_style="bright_blue",
            style="on rgb(24,33,55)",
            expand=False,
            padding=(0, 1),
        )
        self.console.print(Align.right(panel))
        self.console.print()

    def _render_quick_actions(self) -> None:
        if self.orchestrator.session.pending_follow_up_action != "apply_last_prompt":
            return
        self.console.print("Quick actions: [1] apply changes  [ /apply ]", style="yellow")
        self.console.print()

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
