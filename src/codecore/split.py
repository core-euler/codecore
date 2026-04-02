"""Architect / Executor split-mode runtime."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass, field
from typing import Literal

from prompt_toolkit.application import Application
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, VSplit, Window
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.shortcuts.prompt import CompleteStyle
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Frame, TextArea
from rich.console import Console
from rich.markdown import Markdown

from .app import CodeCoreApp, build_orchestrator, build_runtime_dependencies
from .bootstrap import BootstrapContext, bootstrap_application
from .execution.git import GitWorkspace
from .domain.models import ChatMessage
from .domain.enums import PolicyAction
from .domain.results import PolicyDecision
from .execution.shell import summarize_output
from .governance.policy import SimplePolicyEngine
from .infra.session_state import SessionStateStore
from .kernel.command_router import CommandResult
from .kernel.orchestrator import Orchestrator
from .kernel.runtime_state import RuntimeState
from .kernel.session import SessionRuntime, new_session_runtime
from .ui.commands import COMMAND_SPECS, CommandSpec
from .ui.repl import SlashCommandCompleter
from .ui.statusbar import build_status_line

SplitMode = Literal["incremental", "rebuild"]

_SPLIT_GLOBAL_COMMANDS = {"/focus", "/send", "/split", "/roles", "/mode"}
_ARCHITECT_BLOCKED_PREFIXES = (
    "/apply",
    "/autoedit",
    "/replace",
    "/rollback",
    "/undo",
    "/approve",
    "/dismiss",
    "/delegate",
    "/benchmark",
)
_EXECUTOR_BLOCKED_PREFIXES = (
    "/search",
    "/docs",
    "/deps",
    "/proofs",
)
_SPLIT_COMMAND_SPECS: tuple[CommandSpec, ...] = (
    CommandSpec("focus", "/focus <architect|executor>", "Switch the active split pane"),
    CommandSpec("send", '/send ["prompt"]', "Send the last architect plan or explicit prompt to executor"),
    CommandSpec("roles", "/roles", "Show Architect/Executor split overview"),
    CommandSpec("split", "/split", "Alias for /roles"),
    CommandSpec("mode", "/mode [incremental|rebuild]", "Show or change Architect/Executor execution mode"),
)


class ReadOnlyArchitectPolicy(SimplePolicyEngine):
    def evaluate_command(self, command: str) -> PolicyDecision:
        decision = super().evaluate_command(command)
        if decision.risk_level.value == "read_only":
            return decision
        return PolicyDecision(
            action=PolicyAction.DENY,
            risk_level=decision.risk_level,
            reason="Architect role is read-only in split mode.",
            safer_alternative="Use Executor for workspace mutations.",
        )


@dataclass(slots=True)
class _CurrentOrchestratorProxy:
    coordinator: "SplitCoordinator"

    def __getattr__(self, name: str):
        return getattr(self.coordinator.current.orchestrator, name)

    @property
    def command_specs(self) -> tuple[CommandSpec, ...]:
        return _SPLIT_COMMAND_SPECS + COMMAND_SPECS


@dataclass(slots=True)
class SplitRoleRuntime:
    role: str
    orchestrator: Orchestrator


@dataclass(slots=True)
class SplitCoordinator:
    architect: SplitRoleRuntime
    executor: SplitRoleRuntime
    active_role: str = "architect"
    execution_mode: SplitMode = "incremental"
    last_hook: str | None = None
    recent_system_events: list[str] = field(default_factory=list)

    async def start(self) -> None:
        await self.architect.orchestrator.start()
        await self.executor.orchestrator.start()

    async def stop(self) -> None:
        await self.architect.orchestrator.stop()
        await self.executor.orchestrator.stop()

    @property
    def current(self) -> SplitRoleRuntime:
        return self.architect if self.active_role == "architect" else self.executor

    async def handle_line(self, line: str) -> CommandResult:
        stripped = line.strip()
        if not stripped:
            return CommandResult()
        if stripped.startswith("/"):
            head = stripped.split(maxsplit=1)[0]
            if head in _SPLIT_GLOBAL_COMMANDS:
                return await self._handle_global_command(stripped)
        if self.active_role == "architect" and any(stripped.startswith(prefix) for prefix in _ARCHITECT_BLOCKED_PREFIXES):
            return CommandResult(
                output="Architect role is read-only. Switch focus to executor or use /send.",
                is_error=True,
            )
        if self.active_role == "executor" and any(stripped.startswith(prefix) for prefix in _EXECUTOR_BLOCKED_PREFIXES):
            return CommandResult(
                output="Research commands are reserved for Architect in split mode. Use /focus architect.",
                is_error=True,
            )
        role = self.current.role
        before = self._workspace_snapshot() if role == "executor" else ()
        result = await self.current.orchestrator.handle_line(line)
        if self.current.role == "executor" and not result.is_error and result.output:
            self._record_executor_hook(result, before=before, after=self._workspace_snapshot())
        if result.output:
            self._remember_system_event(role, result.output)
        return self._prefix_result(role, result)

    async def _handle_global_command(self, line: str) -> CommandResult:
        if line.startswith("/focus"):
            target = line.split(maxsplit=1)[1].strip().lower() if len(line.split(maxsplit=1)) > 1 else ""
            if target not in {"architect", "executor"}:
                return CommandResult(output="Usage: /focus <architect|executor>", is_error=True)
            self.active_role = target
            return CommandResult(output=f"Focus switched to {target}.")
        if line.startswith("/mode"):
            target = line.split(maxsplit=1)[1].strip().lower() if len(line.split(maxsplit=1)) > 1 else ""
            if not target:
                return CommandResult(output=f"Split mode: {self.execution_mode}.")
            if target not in {"incremental", "rebuild"}:
                return CommandResult(output="Usage: /mode [incremental|rebuild]", is_error=True)
            self.execution_mode = target  # type: ignore[assignment]
            return CommandResult(output=f"Split mode set to {target}.")
        if line.startswith("/roles") or line.startswith("/split"):
            return CommandResult(output=self.render_overview(), render_mode="markdown")
        if line.startswith("/send"):
            if self.active_role != "architect":
                return CommandResult(output="`/send` is only available while focused on architect.", is_error=True)
            parts = line.split(maxsplit=1)
            payload = parts[1].strip() if len(parts) > 1 else self._last_architect_message()
            if not payload:
                return CommandResult(output="Architect has no message to send.", is_error=True)
            executor_prompt = self._compose_executor_prompt(payload)
            before = self._workspace_snapshot()
            result = await self.executor.orchestrator.handle_line(executor_prompt)
            after = self._workspace_snapshot()
            self._record_executor_hook(result, before=before, after=after)
            if not result.is_error and result.output:
                self.active_role = "architect"
                return CommandResult(
                    output=(self.last_hook or "") + "\n\n" + self._prefixed_output("executor", result.output),
                    render_mode="markdown",
                )
            return CommandResult(
                output=(self.last_hook or "") + ("\n\n" + self._prefixed_output("executor", result.output) if result.output else ""),
                is_error=result.is_error,
                render_mode="markdown" if self.last_hook else result.render_mode,
                should_exit=result.should_exit,
            )
        return CommandResult(output=f"Unknown split command: {line}", is_error=True)

    def render_overview(self) -> str:
        lines = [
            f"## Split Mode\n- execution: `{self.execution_mode}`\n- focus: `{self.active_role}`",
            "",
            f"## Architect {'<-- active' if self.active_role == 'architect' else ''}",
            build_status_line(self.architect.orchestrator.session, self.architect.orchestrator.runtime_state),
            self._last_message_summary(self.architect.orchestrator.session),
            "",
            f"## Executor {'<-- active' if self.active_role == 'executor' else ''}",
            build_status_line(self.executor.orchestrator.session, self.executor.orchestrator.runtime_state),
            self._last_message_summary(self.executor.orchestrator.session),
        ]
        if self.last_hook:
            lines.extend(["", "## Latest Hook", self.last_hook])
        return "\n".join(lines)

    def _record_executor_hook(
        self,
        result: CommandResult,
        *,
        before: tuple[str, ...],
        after: tuple[str, ...],
    ) -> None:
        executor = self.executor.orchestrator
        payload = {
            "status": "error" if result.is_error else "complete",
            "mode": self.execution_mode,
            "files_changed": list(after),
            "files_created": [path for path in after if path not in before],
            "summary": summarize_output(result.output or "<no output>", max_chars=220).rendered,
            "errors": [result.output] if result.is_error and result.output else [],
            "tokens_used": executor.session.last_context_token_count,
            "cost_usd": round(executor.session.total_cost_usd, 4),
        }
        hook = (
            "[hook] Executor completed\n"
            f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```"
        )
        self.last_hook = hook
        self.architect.orchestrator.session.transcript.append(ChatMessage(role="hook", content=hook))
        self._remember_system_event("architect", hook)

    def _workspace_snapshot(self) -> tuple[str, ...]:
        git_workspace: GitWorkspace | None = getattr(self.executor.orchestrator, "git_workspace", None)
        if git_workspace is not None and git_workspace.is_repository():
            return tuple(sorted(git_workspace.changed_files()))
        return tuple(sorted(self.executor.orchestrator.session.active_files))

    def _compose_executor_prompt(self, payload: str) -> str:
        verified = self._verified_facts_block()
        if "## Task" in payload or "## Задача" in payload:
            return self._prepend_mode_rules(payload, verified=verified)
        return "\n".join(
            (
                "## Task",
                payload,
                "",
                "## Context",
                "- Verified facts from Architect should be treated as ground truth for this run.",
                "",
                *verified,
                "",
                *self._mode_rules(),
            )
        )

    def _prepend_mode_rules(self, payload: str, *, verified: tuple[str, ...]) -> str:
        sections = ["## Execution Mode", f"- {self.execution_mode}", ""]
        if verified:
            sections.extend((*verified, ""))
        sections.extend((*self._mode_rules(), "", payload))
        return "\n".join(sections)

    def _verified_facts_block(self) -> tuple[str, ...]:
        proofs = self.architect.orchestrator.session.recent_proofs
        if not proofs:
            return ()
        lines = ["## Verified Facts"]
        for item in proofs[-5:]:
            title = item.get("title") or item.get("claim") or "proof"
            url = item.get("url") or ""
            snippet = item.get("snippet") or ""
            if url:
                lines.append(f"- {title} | {url} | {snippet}".strip())
            else:
                lines.append(f"- {title} | {snippet}".strip())
        return tuple(lines)

    def _mode_rules(self) -> tuple[str, ...]:
        if self.execution_mode == "rebuild":
            return (
                "## Rules",
                "- Source of truth: documentation, tests, and verified facts from Architect.",
                "- You may rebuild the targeted module when the existing implementation conflicts with the verified plan.",
                "- Keep changes scoped to the requested area; do not rewrite unrelated parts of the project.",
                "- If requirements are missing, stop and return a precise blocker instead of guessing.",
            )
        return (
            "## Rules",
            "- Default mode is incremental: do not refactor working code unless explicitly instructed.",
            "- Do not change dependencies, schema, or unrelated modules without explicit approval from Architect.",
            "- Respect existing project patterns and keep edits narrowly scoped.",
            "- If a safe incremental implementation is impossible, stop and explain the blocker clearly.",
        )

    @staticmethod
    def _prefixed_output(role: str, output: str) -> str:
        return f"[{role}] {output}"

    def _prefix_result(self, role: str, result: CommandResult) -> CommandResult:
        if not result.output:
            return result
        return CommandResult(
            output=self._prefixed_output(role, result.output),
            should_exit=result.should_exit,
            is_error=result.is_error,
            render_mode=result.render_mode,
        )

    def _last_architect_message(self) -> str:
        transcript = self.architect.orchestrator.session.transcript
        for message in reversed(transcript):
            if message.role == "assistant":
                return message.content.strip()
        return self.architect.orchestrator.session.last_user_prompt or ""

    def render_role_panel(self, role: str) -> str:
        runtime = self.architect if role == "architect" else self.executor
        session = runtime.orchestrator.session
        state = runtime.orchestrator.runtime_state
        lines = [
            f"{role.upper()} {'<ACTIVE>' if self.active_role == role else ''}".rstrip(),
            build_status_line(session, state),
        ]
        if session.active_skills:
            lines.append("skills: " + ", ".join(session.active_skills))
        if session.active_files:
            lines.append("files: " + ", ".join(session.active_files[-6:]))
        lines.extend(("", *self._transcript_lines(session)))
        events = self._recent_events_for(role)
        if events:
            lines.extend(("", "latest events:", *events))
        return "\n".join(lines).strip()

    def render_session_footer(self) -> str:
        architect = self.architect.orchestrator.session
        executor = self.executor.orchestrator.session
        total_cost = architect.total_cost_usd + executor.total_cost_usd
        total_requests = architect.request_count + executor.request_count
        return (
            f"session mode={self.execution_mode} | focus={self.active_role} | "
            f"req={total_requests} | cost=${total_cost:.4f} | "
            "Tab switch focus | Enter submit | /send dispatches Architect plan"
        )

    def _recent_events_for(self, role: str) -> tuple[str, ...]:
        scoped: list[str] = []
        prefix = f"[{role}] "
        for item in reversed(self.recent_system_events):
            if item.startswith(prefix):
                scoped.append(item[len(prefix):])
            if len(scoped) >= 2:
                break
        return tuple(reversed(scoped))

    def _remember_system_event(self, role: str, output: str) -> None:
        summary = summarize_output(output, max_chars=280).rendered
        self.recent_system_events.append(f"[{role}] {summary}")
        self.recent_system_events = self.recent_system_events[-12:]

    @staticmethod
    def _transcript_lines(session: SessionRuntime) -> tuple[str, ...]:
        if not session.transcript:
            return ("_empty_",)
        lines: list[str] = []
        for message in session.transcript[-10:]:
            content = summarize_output(message.content, max_chars=420).rendered
            lines.append(f"[{message.role}] {content}")
        return tuple(lines)

    @staticmethod
    def _last_message_summary(session: SessionRuntime) -> str:
        if not session.transcript:
            return "_empty_"
        message = session.transcript[-1]
        return f"**{message.role}:** {summarize_output(message.content, max_chars=180).rendered}"


@dataclass(slots=True)
class SplitCodeCoreApp:
    bootstrap: BootstrapContext
    coordinator: SplitCoordinator
    console: Console
    history_path: str | None = None
    _application: Application | None = field(init=False, default=None)
    _architect_view: TextArea | None = field(init=False, default=None)
    _executor_view: TextArea | None = field(init=False, default=None)
    _status_view: TextArea | None = field(init=False, default=None)
    _input_view: TextArea | None = field(init=False, default=None)
    _message_view: TextArea | None = field(init=False, default=None)
    _busy: bool = field(init=False, default=False)

    def run(self) -> int:
        print(self.bootstrap.startup_summary() + f" | mode=split/{self.coordinator.execution_mode}")
        return asyncio.run(self._run())

    async def _run(self) -> int:
        await self.coordinator.start()
        try:
            if sys.stdin.isatty():
                return await self._run_interactive()
            return await self._run_stream()
        finally:
            await self.coordinator.stop()

    async def _run_interactive(self) -> int:
        history = FileHistory(self.history_path) if self.history_path else None
        self._application = self._build_fullscreen_application(history)
        self._refresh_views()
        return await self._application.run_async()

    async def _run_stream(self) -> int:
        for raw_line in sys.stdin:
            result = await self.coordinator.handle_line(raw_line.rstrip("\n"))
            if result.output:
                self._render_output(result)
            if result.should_exit:
                return 0
        return 0

    def _render_output(self, result: CommandResult) -> None:
        if result.render_mode == "markdown" and not result.is_error:
            self.console.print(Markdown(result.output))
            self.console.print()
            return
        self.console.print(result.output, style="red" if result.is_error else None, markup=False, highlight=False)
        self.console.print()

    @staticmethod
    def _status_text(line: str) -> str:
        stripped = line.strip()
        if stripped.startswith("/send"):
            return "sending plan to executor"
        if stripped.startswith("/focus"):
            return "switching focus"
        if stripped.startswith("/mode"):
            return "updating split mode"
        return "coordinating split session"

    def _build_fullscreen_application(self, history) -> Application:
        proxy = _CurrentOrchestratorProxy(self.coordinator)
        key_bindings = KeyBindings()

        @key_bindings.add("tab")
        def _toggle_focus(event) -> None:
            self.coordinator.active_role = "executor" if self.coordinator.active_role == "architect" else "architect"
            self._refresh_views(message=f"focus={self.coordinator.active_role}")

        @key_bindings.add("c-c")
        def _interrupt(event) -> None:
            event.app.exit(result=0)

        architect_view = TextArea(read_only=True, focusable=False, scrollbar=True, wrap_lines=True, style="class:pane")
        executor_view = TextArea(read_only=True, focusable=False, scrollbar=True, wrap_lines=True, style="class:pane")
        status_view = TextArea(read_only=True, focusable=False, height=1, style="class:status")
        message_view = TextArea(read_only=True, focusable=False, height=2, style="class:message")
        input_view = TextArea(
            text="",
            multiline=False,
            wrap_lines=False,
            history=history,
            completer=SlashCommandCompleter(proxy),
            complete_while_typing=True,
            accept_handler=self._accept_input,
            prompt=self._input_prompt(),
            style="class:input",
        )

        self._architect_view = architect_view
        self._executor_view = executor_view
        self._status_view = status_view
        self._message_view = message_view
        self._input_view = input_view

        layout = Layout(
            HSplit(
                [
                    VSplit(
                        [
                            Frame(architect_view, title=self._pane_title("architect")),
                            Frame(executor_view, title=self._pane_title("executor")),
                        ],
                        padding=1,
                    ),
                    Window(height=1, char="─", style="class:divider"),
                    status_view,
                    message_view,
                    input_view,
                ]
            )
        )
        return Application(
            layout=layout,
            key_bindings=key_bindings,
            full_screen=True,
            mouse_support=False,
            style=Style.from_dict(
                {
                    "pane": "bg:#0f1720 #d7dde8",
                    "frame.label": "bg:#1b2a3a #d7dde8 bold",
                    "status": "bg:#25364a #d7dde8",
                    "message": "bg:#111827 #b7c3d0",
                    "input": "bg:#0b1220 #f8fafc",
                    "divider": "#334155",
                }
            ),
        )

    def _accept_input(self, buffer) -> bool:
        line = buffer.text
        buffer.text = ""
        if self._busy:
            self._refresh_views(message="busy: wait for the current action to finish")
            return False
        asyncio.create_task(self._process_line(line))
        return False

    async def _process_line(self, line: str) -> None:
        if not line.strip():
            self._refresh_views()
            return
        self._busy = True
        self._refresh_views(message=self._status_text(line))
        result = await self.coordinator.handle_line(line)
        message = summarize_output(result.output or "ok", max_chars=280).rendered if result.output else "ok"
        self._busy = False
        self._refresh_views(message=message)
        if result.should_exit and self._application is not None:
            self._application.exit(result=0)

    def _refresh_views(self, *, message: str | None = None) -> None:
        if self._architect_view is None or self._executor_view is None or self._status_view is None or self._input_view is None or self._message_view is None:
            return
        self._architect_view.text = self.coordinator.render_role_panel("architect")
        self._executor_view.text = self.coordinator.render_role_panel("executor")
        self._status_view.text = self.coordinator.render_session_footer()
        self._message_view.text = message or self.coordinator.last_hook or "ready"
        self._input_view.prompt = self._input_prompt()
        container = self._application.layout.container if self._application is not None else None
        if isinstance(container, HSplit):
            top = container.children[0]
            if isinstance(top, VSplit):
                left = top.children[0]
                right = top.children[1]
                if isinstance(left, Frame):
                    left.title = self._pane_title("architect")
                if isinstance(right, Frame):
                    right.title = self._pane_title("executor")
        if self._application is not None:
            self._application.invalidate()

    def _pane_title(self, role: str) -> str:
        marker = " *" if self.coordinator.active_role == role else ""
        role_name = "ARCHITECT" if role == "architect" else "EXECUTOR"
        return f"{role_name}{marker}"

    def _input_prompt(self) -> str:
        busy = "busy" if self._busy else self.coordinator.active_role
        return f"({busy})> "


def create_split_app(*, mode: SplitMode = "incremental") -> SplitCodeCoreApp:
    bootstrap = bootstrap_application()
    deps = build_runtime_dependencies(bootstrap)

    architect_session = new_session_runtime()
    architect_state = RuntimeState.default()
    executor_session = new_session_runtime()
    executor_state = RuntimeState.default()

    _apply_split_defaults(deps.registry, deps.skill_registry, architect_session, architect_state, executor_session, executor_state)
    architect_session.task_tag = bootstrap.session.task_tag
    executor_session.task_tag = bootstrap.session.task_tag

    architect = build_orchestrator(
        bootstrap,
        deps,
        session=architect_session,
        runtime_state=architect_state,
        policy_engine=ReadOnlyArchitectPolicy(),
        session_store=SessionStateStore(
            bootstrap.settings.config_dir / "architect-session.json",
            bootstrap.settings.config_dir / "architect-context.md",
            bootstrap.settings.context_snapshot_dir / "architect",
        ),
    )
    executor = build_orchestrator(
        bootstrap,
        deps,
        session=executor_session,
        runtime_state=executor_state,
        session_store=SessionStateStore(
            bootstrap.settings.config_dir / "executor-session.json",
            bootstrap.settings.config_dir / "executor-context.md",
            bootstrap.settings.context_snapshot_dir / "executor",
        ),
    )
    coordinator = SplitCoordinator(
        architect=SplitRoleRuntime(role="architect", orchestrator=architect),
        executor=SplitRoleRuntime(role="executor", orchestrator=executor),
        execution_mode=mode,
    )
    return SplitCodeCoreApp(
        bootstrap=bootstrap,
        coordinator=coordinator,
        console=Console(),
        history_path=str(bootstrap.settings.repl_history_path),
    )


def _apply_split_defaults(registry, skill_registry, architect_session: SessionRuntime, architect_state: RuntimeState, executor_session: SessionRuntime, executor_state: RuntimeState) -> None:
    architect_state.manual_model_alias = _pick_alias(registry, ("ds-r1", "claude", "ds-v3", "mock"))
    executor_state.manual_model_alias = _pick_alias(registry, ("codestral", "ds-v3", "mock"))
    if skill_registry.has_skill("discover"):
        architect_session.active_skills = ["discover"]
        architect_state.active_skills = ["discover"]
    if skill_registry.has_skill("implement"):
        executor_session.active_skills = ["implement"]
        executor_state.active_skills = ["implement"]


def _pick_alias(registry, aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        if registry.by_alias(alias) is not None or registry.by_model_id(alias) is not None:
            return alias
    return None
