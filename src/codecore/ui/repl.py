"""Interactive terminal REPL."""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path

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

from ..domain.enums import TaskTag
from ..kernel.orchestrator import Orchestrator
from .commands import COMMAND_SPECS
from .statusbar import build_status_line

_IGNORED_COMPLETION_DIRS = {
    ".git",
    ".venv",
    ".codecore-home",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
}

_COMMAND_OPTIONS: dict[str, tuple[str, ...]] = {
    "run": ("--verify",),
    "verify": (),
    "autoedit": ("--verify",),
    "replace": ("--verify",),
    "delegate": ("--pipeline", "--verify", "--apply"),
    "benchmark": ("--models", "--pipeline", "--verify"),
}


class SlashCommandCompleter(Completer):
    def __init__(self, orchestrator: Orchestrator | None = None) -> None:
        self._orchestrator = orchestrator

    def get_completions(self, document, complete_event):
        text_before_cursor = document.text_before_cursor
        lines = text_before_cursor.splitlines() or [""]
        current_line = lines[-1].lstrip()
        if not current_line.startswith("/"):
            return
        if " " in current_line:
            yield from self._argument_completions(current_line)
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

    def _argument_completions(self, current_line: str):
        parts = current_line.split()
        if not parts:
            return
        command = parts[0].removeprefix("/")
        trailing_space = current_line.endswith(" ")
        args = parts[1:]
        current_token = "" if trailing_space or not args else args[-1]
        arg_index = len(args) if trailing_space else max(len(args) - 1, 0)
        previous_token = args[arg_index - 1] if arg_index > 0 else ""

        if previous_token == "--pipeline":
            yield from self._yield_values(self._pipeline_candidates(), current_token, meta="pipeline")
            return
        if previous_token == "--models":
            yield from self._yield_csv_values(self._model_candidates(), current_token, meta="model")
            return

        if current_token.startswith("-") or (not current_token and previous_token != "--pipeline"):
            options = _COMMAND_OPTIONS.get(command, ())
            if options:
                yield from self._yield_values(options, current_token, meta="option")

        if command == "model" and arg_index == 0:
            yield from self._yield_values(self._model_candidates(), current_token, meta="model")
        elif command == "skill" and arg_index == 0:
            yield from self._yield_values(("clear", *self._skill_candidates()), current_token, meta="skill")
        elif command == "tag" and arg_index == 0:
            yield from self._yield_values(tuple(tag.value for tag in TaskTag), current_token, meta="task tag")
        elif command == "rate" and arg_index == 0:
            yield from self._yield_values(tuple(str(index) for index in range(1, 6)), current_token, meta="rating")
        elif command == "approve" and arg_index == 0:
            yield from self._yield_values(self._approval_candidates(include_session_shortcut=True), current_token, meta="approval")
        elif command == "dismiss" and arg_index == 0:
            yield from self._yield_values(self._dismiss_candidates(), current_token, meta="approval")
        elif command == "rollback" and arg_index == 0:
            yield from self._yield_values(("latest", *self._active_file_candidates()), current_token, meta="path")
        elif command in {"add", "pin"}:
            yield from self._yield_values(self._workspace_file_candidates(current_token), current_token, meta="file")
        elif command in {"drop", "unpin"}:
            yield from self._yield_values(self._active_file_candidates(), current_token, meta="active file")
        elif command in {"diff", "undo"}:
            candidates = self._active_file_candidates() or self._workspace_file_candidates(current_token)
            yield from self._yield_values(candidates, current_token, meta="path")
        elif command == "replace" and self._replace_expects_path(args, arg_index):
            yield from self._yield_values(self._workspace_file_candidates(current_token), current_token, meta="file")

    @staticmethod
    def _yield_values(values: tuple[str, ...], current_token: str, *, meta: str):
        seen: set[str] = set()
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            if current_token and not value.startswith(current_token):
                continue
            yield Completion(text=value, start_position=-len(current_token), display=value, display_meta=meta)

    @staticmethod
    def _yield_csv_values(values: tuple[str, ...], current_token: str, *, meta: str):
        if "," not in current_token:
            yield from SlashCommandCompleter._yield_values(values, current_token, meta=meta)
            return
        used = [part for part in current_token.split(",")[:-1] if part]
        current_part = current_token.split(",")[-1]
        prefix = ",".join(used)
        for value in values:
            if value in used:
                continue
            if current_part and not value.startswith(current_part):
                continue
            completed = value if not prefix else f"{prefix},{value}"
            yield Completion(text=completed, start_position=-len(current_token), display=completed, display_meta=meta)

    def _model_candidates(self) -> tuple[str, ...]:
        if self._orchestrator is None:
            return ()
        values: list[str] = []
        for item in self._orchestrator.provider_registry.list_registered():
            if item.model.alias:
                values.append(item.model.alias)
            values.append(item.model.id)
        return tuple(dict.fromkeys(values))

    def _skill_candidates(self) -> tuple[str, ...]:
        registry = getattr(self._orchestrator, "skill_registry", None) if self._orchestrator is not None else None
        if registry is None:
            return ()
        if hasattr(registry, "skill_ids"):
            return tuple(getattr(registry, "skill_ids")())
        skills = getattr(registry, "_skills", None)
        if isinstance(skills, dict):
            return tuple(sorted(skills))
        return ()

    def _approval_candidates(self, *, include_session_shortcut: bool) -> tuple[str, ...]:
        manager = getattr(self._orchestrator, "approval_manager", None) if self._orchestrator is not None else None
        if manager is None:
            return ("latest", "1", "2") if include_session_shortcut else ("latest", "3")
        pending = manager.list_pending()
        values = ["latest"]
        if include_session_shortcut:
            values.extend(("1", "2"))
        else:
            values.append("3")
        values.extend(item.approval_id for item in pending)
        return tuple(values)

    def _dismiss_candidates(self) -> tuple[str, ...]:
        return self._approval_candidates(include_session_shortcut=False)

    def _pipeline_candidates(self) -> tuple[str, ...]:
        runner = getattr(self._orchestrator, "multi_agent_runner", None) if self._orchestrator is not None else None
        if runner is None:
            return ()
        return tuple(pipeline.pipeline_id for pipeline in runner.list_pipelines())

    def _active_file_candidates(self) -> tuple[str, ...]:
        session = getattr(self._orchestrator, "session", None) if self._orchestrator is not None else None
        if session is None:
            return ()
        return tuple(session.active_files)

    def _workspace_file_candidates(self, current_token: str) -> tuple[str, ...]:
        if self._orchestrator is None:
            return ()
        root = self._orchestrator.context_manager.project_root
        normalized_prefix = current_token or ""
        candidates: list[str] = []
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [name for name in dirnames if name not in _IGNORED_COMPLETION_DIRS]
                for filename in filenames:
                    path = Path(dirpath, filename)
                    try:
                        relative = str(path.relative_to(root))
                    except ValueError:
                        continue
                    if normalized_prefix and not relative.startswith(normalized_prefix):
                        continue
                    candidates.append(relative)
                    if len(candidates) >= 200:
                        return tuple(candidates)
        except OSError:
            return ()
        return tuple(candidates)

    @staticmethod
    def _replace_expects_path(args: list[str], arg_index: int) -> bool:
        non_flag_index = 0
        for index, token in enumerate(args):
            if token == "--verify":
                continue
            if index == arg_index:
                return non_flag_index == 0
            non_flag_index += 1
        return non_flag_index == 0


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
            completer=SlashCommandCompleter(self.orchestrator),
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
