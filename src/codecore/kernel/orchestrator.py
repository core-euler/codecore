"""Main runtime orchestration loop."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..context.manager import ContextManager
from ..domain.contracts import ContextComposer, PolicyEngine, SkillRegistry, ToolExecutor, VerificationEngine
from ..domain.enums import EventKind, PolicyAction, RiskLevel, TaskTag
from ..domain.events import EventEnvelope
from ..domain.models import ChatMessage, ChatRequest
from ..domain.results import PolicyDecision, VerificationResult
from ..execution.audit import FileChangeAudit
from ..execution.approvals import ApprovalManager
from ..execution.git import GitWorkspace
from ..execution.patches import PatchService
from ..execution.sandbox import SandboxProfile
from ..execution.shell import summarize_output
from ..kernel.command_router import CommandResult, CommandRouter
from ..kernel.event_bus import EventBus
from ..kernel.runtime_state import RuntimeState
from ..kernel.session import SessionRuntime, new_turn_context
from ..providers.adapters.base import AdapterFactory
from ..providers.broker import BrokerError, PolicyDrivenBroker
from ..providers.health import ProviderHealthService
from ..providers.registry import ProviderRegistry
from ..telemetry.analytics import TelemetryAnalytics
from ..ui.commands import HELP_TEXT


@dataclass(slots=True)
class Orchestrator:
    session: SessionRuntime
    runtime_state: RuntimeState
    provider_registry: ProviderRegistry
    broker: PolicyDrivenBroker
    health_service: ProviderHealthService
    adapter_factory: AdapterFactory
    context_manager: ContextManager
    context_composer: ContextComposer
    event_bus: EventBus
    skill_registry: SkillRegistry | None = None
    analytics_service: TelemetryAnalytics | None = None
    tool_executor: ToolExecutor | None = None
    policy_engine: PolicyEngine | None = None
    git_workspace: GitWorkspace | None = None
    patch_service: PatchService | None = None
    file_change_audit: FileChangeAudit | None = None
    approval_manager: ApprovalManager | None = None
    verification_engine: VerificationEngine | None = None
    command_router: CommandRouter = field(init=False)

    def __post_init__(self) -> None:
        self.command_router = CommandRouter()
        self.command_router.register("help", self._cmd_help)
        self.command_router.register("status", self._cmd_status)
        self.command_router.register("stats", self._cmd_stats)
        self.command_router.register("run", self._cmd_run)
        self.command_router.register("replace", self._cmd_replace)
        self.command_router.register("rollback", self._cmd_rollback)
        self.command_router.register("retry", self._cmd_retry)
        self.command_router.register("approvals", self._cmd_approvals)
        self.command_router.register("approve", self._cmd_approve)
        self.command_router.register("verify", self._cmd_verify)
        self.command_router.register("diff", self._cmd_diff)
        self.command_router.register("undo", self._cmd_undo)
        self.command_router.register("model", self._cmd_model)
        self.command_router.register("skill", self._cmd_skill)
        self.command_router.register("tag", self._cmd_tag)
        self.command_router.register("rate", self._cmd_rate)
        self.command_router.register("ping", self._cmd_ping)
        self.command_router.register("add", self._cmd_add)
        self.command_router.register("drop", self._cmd_drop)
        self.command_router.register("pin", self._cmd_add)
        self.command_router.register("unpin", self._cmd_drop)
        self.command_router.register("clear", self._cmd_clear)
        self.command_router.register("exit", self._cmd_exit)

    async def start(self) -> None:
        await self.health_service.refresh(force=True)
        await self.event_bus.publish(
            EventEnvelope.create(
                kind=EventKind.SESSION_STARTED,
                session_id=self.session.session_id,
                task_tag=self.session.task_tag,
            )
        )

    async def stop(self) -> None:
        await self.event_bus.publish(
            EventEnvelope.create(
                kind=EventKind.SESSION_FINISHED,
                session_id=self.session.session_id,
                task_tag=self.session.task_tag,
                provider_id=self.runtime_state.active_provider,
                model_id=self.runtime_state.active_model,
                skill_ids=tuple(self.session.active_skills),
            )
        )

    async def handle_line(self, line: str) -> CommandResult:
        stripped = line.strip()
        if not stripped:
            return CommandResult()
        if stripped.startswith("/"):
            return await self.command_router.dispatch(stripped)
        return await self._handle_prompt(stripped)

    async def _handle_prompt(self, prompt: str) -> CommandResult:
        turn = new_turn_context(prompt)
        request = ChatRequest(
            messages=(ChatMessage(role="user", content=prompt),),
            task_tag=self.session.task_tag,
            model_hint=self.runtime_state.manual_model_alias,
        )
        request = await self.context_composer.compose(request)
        if self.session.active_skills:
            await self.event_bus.publish(
                EventEnvelope.create(
                    kind=EventKind.SKILL_ACTIVATED,
                    session_id=self.session.session_id,
                    turn_id=turn.turn_id,
                    task_tag=self.session.task_tag,
                    skill_ids=tuple(self.session.active_skills),
                    payload={"pinned_skills": tuple(self.runtime_state.active_skills)},
                )
            )
        try:
            routes = await self.broker.candidate_routes(request)
        except BrokerError as exc:
            return CommandResult(output=str(exc), is_error=True)

        last_error: Exception | None = None
        for index, route in enumerate(routes):
            self.runtime_state.active_provider = route.provider_id
            self.runtime_state.active_model = route.alias or route.model_id
            await self.event_bus.publish(
                EventEnvelope.create(
                    kind=EventKind.PROVIDER_SELECTED,
                    session_id=self.session.session_id,
                    turn_id=turn.turn_id,
                    task_tag=self.session.task_tag,
                    provider_id=route.provider_id,
                    model_id=route.model_id,
                    skill_ids=tuple(self.session.active_skills),
                    payload={"alias": route.alias, "attempt": index + 1},
                )
            )

            adapter = self.adapter_factory.create(route)
            try:
                result = await adapter.chat(request)
            except Exception as exc:
                last_error = exc
                if index + 1 < len(routes):
                    next_route = routes[index + 1]
                    await self.event_bus.publish(
                        EventEnvelope.create(
                            kind=EventKind.FALLBACK_TRIGGERED,
                            session_id=self.session.session_id,
                            turn_id=turn.turn_id,
                            task_tag=self.session.task_tag,
                            provider_id=route.provider_id,
                            model_id=route.model_id,
                            skill_ids=tuple(self.session.active_skills),
                            payload={
                                "failed_alias": route.alias,
                                "error": str(exc),
                                "next_provider_id": next_route.provider_id,
                                "next_model_id": next_route.model_id,
                                "next_alias": next_route.alias,
                            },
                        )
                    )
                    continue
                break

            self.session.request_count += 1
            self.session.total_cost_usd += result.cost_usd or 0.0
            self.session.last_model_alias = route.alias or route.model_id
            self.session.last_turn_id = turn.turn_id
            await self.event_bus.publish(
                EventEnvelope.create(
                    kind=EventKind.MODEL_INVOKED,
                    session_id=self.session.session_id,
                    turn_id=turn.turn_id,
                    task_tag=self.session.task_tag,
                    provider_id=route.provider_id,
                    model_id=route.model_id,
                    skill_ids=tuple(self.session.active_skills),
                    payload={
                        "input_tokens": result.input_tokens,
                        "output_tokens": result.output_tokens,
                        "latency_ms": result.latency_ms,
                        "cost_usd": result.cost_usd,
                        "model_alias": route.alias or route.model_id,
                        "prompt": prompt,
                        "response_excerpt": result.text[:500],
                        "response_text": result.text,
                        "active_files": tuple(self.session.active_files),
                    },
                )
            )
            return CommandResult(output=result.text)

        if last_error is None:
            return CommandResult(output="No provider routes were available for invocation.", is_error=True)
        return CommandResult(output=f"All provider routes failed: {last_error}", is_error=True)

    async def _cmd_help(self, _: list[str]) -> CommandResult:
        return CommandResult(output=HELP_TEXT)

    async def _cmd_status(self, _: list[str]) -> CommandResult:
        snapshot = self.health_service.last_snapshot()
        health_text = "\n".join(
            f"  {name}: {status.state.value} ({status.detail})" for name, status in sorted(snapshot.items())
        ) or "  <no health data>"
        files = ", ".join(self.session.active_files) if self.session.active_files else "<none>"
        active_skills = ", ".join(self.session.active_skills) if self.session.active_skills else "<none>"
        pinned_skills = ", ".join(self.runtime_state.active_skills) if self.runtime_state.active_skills else "<none>"
        recommended_model = "<none>"
        if self.analytics_service is not None:
            recommendation = self.analytics_service.build_report(task_tag=self.session.task_tag).recommendation
            if recommendation.model is not None:
                recommended_model = recommendation.model
        text = (
            f"session={self.session.session_id}\n"
            f"task_tag={self.session.task_tag.value}\n"
            f"provider={self.runtime_state.active_provider or 'auto'}\n"
            f"model={self.runtime_state.active_model or self.runtime_state.manual_model_alias or 'auto'}\n"
            f"recommended_model={recommended_model}\n"
            f"active_files={files}\n"
            f"active_skills={active_skills}\n"
            f"pinned_skills={pinned_skills}\n"
            f"pending_approvals={len(self.approval_manager.list_pending()) if self.approval_manager is not None else 0}\n"
            f"last_turn_id={self.session.last_turn_id or '<none>'}\n"
            f"last_rating={self.session.last_rating if self.session.last_rating is not None else '<none>'}\n"
            f"last_verification={self.session.last_verification_summary or '<none>'}\n"
            f"last_failure={self.session.last_failed_action or '<none>'}\n"
            f"requests={self.session.request_count}\n"
            f"cost=${self.session.total_cost_usd:.6f}\n"
            f"health:\n{health_text}"
        )
        return CommandResult(output=text)

    async def _cmd_stats(self, _: list[str]) -> CommandResult:
        if self.analytics_service is None:
            return CommandResult(output="Analytics service is not configured.", is_error=True)
        report = self.analytics_service.build_report(task_tag=self.session.task_tag)
        return CommandResult(output=report.render_text())

    async def _cmd_run(self, args: list[str]) -> CommandResult:
        if not args:
            return CommandResult(output="Usage: /run <command>", is_error=True)
        if self.tool_executor is None or self.policy_engine is None:
            return CommandResult(output="Execution layer is not configured.", is_error=True)
        verify_after = False
        if args and args[0] == "--verify":
            verify_after = True
            args = args[1:]
        if not args:
            return CommandResult(output="Usage: /run [--verify] <command>", is_error=True)
        command = " ".join(args)
        decision = await self.policy_engine.evaluate_tool_call(command)
        if decision.action.value != "allow":
            return await self._request_approval_or_block("run", command, decision)
        return await self._execute_shell_command(command, decision, verify_after=verify_after)

    async def _cmd_replace(self, args: list[str]) -> CommandResult:
        if self.patch_service is None:
            return CommandResult(output="Patch service is not configured.", is_error=True)
        verify_after = False
        if args and args[0] == "--verify":
            verify_after = True
            args = args[1:]
        if len(args) != 3:
            return CommandResult(output='Usage: /replace [--verify] <path> <old> <new>', is_error=True)
        path, needle, replacement = args
        decision = PolicyDecision(
            action=PolicyAction.REQUIRE_APPROVAL,
            risk_level=RiskLevel.WORKSPACE_WRITE,
            reason=f"Replacing text in {path} mutates workspace files.",
            safer_alternative="Inspect the file with /add or /diff before approving the edit.",
        )
        return await self._request_approval_or_block(
            "replace",
            f"replace {path}",
            decision,
            metadata={
                "path": path,
                "needle": needle,
                "replacement": replacement,
                "verify_after": verify_after,
            },
        )

    async def _cmd_retry(self, _: list[str]) -> CommandResult:
        if self.session.last_failed_action is None or self.session.last_failed_command is None:
            return CommandResult(output="No failed command is available to retry.", is_error=True)
        if self.session.last_failed_action == "run":
            decision = await self.policy_engine.evaluate_tool_call(self.session.last_failed_command) if self.policy_engine else None
            if decision is None:
                return CommandResult(output="Policy engine is not configured.", is_error=True)
            if decision.action.value != "allow":
                return await self._request_approval_or_block("run", self.session.last_failed_command, decision)
            return await self._execute_shell_command(self.session.last_failed_command, decision)
        if self.session.last_failed_action == "verify":
            return await self._execute_verification(self.session.last_failed_command)
        return CommandResult(output=f"Retry is not supported for action: {self.session.last_failed_action}", is_error=True)

    async def _cmd_rollback(self, args: list[str]) -> CommandResult:
        if self.patch_service is None:
            return CommandResult(output="Patch service is not configured.", is_error=True)
        if not self.session.recent_patches:
            return CommandResult(output="No snapshot-backed patch is available for rollback.", is_error=True)
        target = args[0] if args else "latest"
        index = self._find_patch_checkpoint(target)
        if index is None:
            return CommandResult(output=f"No patch checkpoint found for: {target}", is_error=True)
        path, backup_path = self.session.recent_patches.pop(index)
        self.patch_service.undo(path, backup_path)
        message = f"Rolled back patch: {path}"
        await self.event_bus.publish(
            EventEnvelope.create(
                kind=EventKind.TOOL_FINISHED,
                session_id=self.session.session_id,
                task_tag=self.session.task_tag,
                payload={"command": "rollback", "tool_kind": "patch", "path": path},
            )
        )
        if self.file_change_audit is not None:
            self.file_change_audit.record_restore(
                session_id=self.session.session_id,
                paths=(path,),
                metadata={"source": "patch.rollback"},
            )
        self._remember_tool_output(f"rollback: {path}", message)
        self._clear_failure()
        return CommandResult(output=message)

    async def _cmd_approvals(self, _: list[str]) -> CommandResult:
        if self.approval_manager is None:
            return CommandResult(output="Approval manager is not configured.", is_error=True)
        pending = self.approval_manager.list_pending()
        if not pending:
            return CommandResult(output="No pending approvals.")
        lines = []
        for item in pending:
            lines.append(
                f"{item.approval_id} | {item.action} | {item.risk_level.value} | {item.command} | {item.reason}"
            )
        return CommandResult(output="\n".join(lines))

    async def _cmd_approve(self, args: list[str]) -> CommandResult:
        if not args:
            return CommandResult(output="Usage: /approve <approval-id>", is_error=True)
        if self.approval_manager is None:
            return CommandResult(output="Approval manager is not configured.", is_error=True)
        approval_id = args[0]
        if approval_id == "latest":
            pending = self.approval_manager.list_pending()
            if not pending:
                return CommandResult(output="No pending approvals.", is_error=True)
            approval_id = pending[-1].approval_id
        approval = self.approval_manager.resolve(approval_id)
        if approval is None:
            return CommandResult(output=f"Unknown approval id: {approval_id}", is_error=True)
        decision = PolicyDecision(
            action=PolicyAction.ALLOW,
            risk_level=approval.risk_level,
            reason=approval.reason,
            safer_alternative=approval.safer_alternative,
        )
        if approval.action == "run":
            return await self._execute_shell_command(approval.command, decision, approved=True)
        if approval.action == "replace":
            path = approval.metadata.get("path")
            needle = approval.metadata.get("needle")
            replacement = approval.metadata.get("replacement")
            if not isinstance(path, str) or not isinstance(needle, str) or not isinstance(replacement, str):
                return CommandResult(output="Approval payload for replace is invalid.", is_error=True)
            return await self._apply_replace(
                path,
                needle,
                replacement,
                verify_after=bool(approval.metadata.get("verify_after")),
                approved=True,
            )
        if approval.action == "verify":
            return await self._execute_verification(approval.command or None, approved=True)
        return CommandResult(output=f"Unsupported approval action: {approval.action}", is_error=True)

    async def _cmd_verify(self, args: list[str]) -> CommandResult:
        if self.verification_engine is None:
            return CommandResult(output="Verification engine is not configured.", is_error=True)
        command = " ".join(args) if args else None
        if command and self.policy_engine is not None:
            decision = await self.policy_engine.evaluate_tool_call(command)
            if decision.action.value != "allow":
                return await self._request_approval_or_block("verify", command, decision)
        return await self._execute_verification(command)

    async def _cmd_diff(self, args: list[str]) -> CommandResult:
        if self.git_workspace is None:
            return CommandResult(output="Git workspace is not configured.", is_error=True)
        paths = tuple(args or self.session.active_files)
        diff_text = self.git_workspace.diff_summary(paths)
        self._remember_tool_output("git diff", diff_text)
        return CommandResult(output=diff_text)

    async def _cmd_undo(self, args: list[str]) -> CommandResult:
        if self.git_workspace is None:
            return CommandResult(output="Git workspace is not configured.", is_error=True)
        paths = tuple(args or self.session.active_files)
        await self.event_bus.publish(
            EventEnvelope.create(
                kind=EventKind.TOOL_CALLED,
                session_id=self.session.session_id,
                task_tag=self.session.task_tag,
                payload={"command": "undo", "tool_kind": "git", "paths": paths},
            )
        )
        output = self.git_workspace.restore(paths)
        is_error = output.startswith("Git repository is not initialized") or output.startswith("Undo is unavailable")
        await self.event_bus.publish(
            EventEnvelope.create(
                kind=EventKind.TOOL_FINISHED,
                session_id=self.session.session_id,
                task_tag=self.session.task_tag,
                payload={"command": "undo", "tool_kind": "git", "paths": paths, "result": output},
            )
        )
        if not is_error and self.file_change_audit is not None:
            self.file_change_audit.record_restore(
                session_id=self.session.session_id,
                paths=paths,
                metadata={"source": "git.restore"},
            )
        self._remember_tool_output("git undo", output)
        return CommandResult(output=output, is_error=is_error)

    async def _cmd_model(self, args: list[str]) -> CommandResult:
        if not args:
            self.runtime_state.manual_model_alias = None
            return CommandResult(output="Model pin cleared; broker will auto-select.")
        alias = args[0]
        route = self.provider_registry.by_alias(alias) or self.provider_registry.by_model_id(alias)
        if route is None:
            return CommandResult(output=f"Unknown model alias: {alias}", is_error=True)
        self.runtime_state.manual_model_alias = alias
        return CommandResult(output=f"Pinned model alias: {alias}")

    async def _cmd_skill(self, args: list[str]) -> CommandResult:
        if self.skill_registry is None:
            return CommandResult(output="Skill registry is not configured.", is_error=True)
        if not args:
            available = ", ".join(skill.skill_id for skill in await self.skill_registry.list_skills()) or "<none>"
            pinned = ", ".join(self.runtime_state.active_skills) if self.runtime_state.active_skills else "<none>"
            active = ", ".join(self.session.active_skills) if self.session.active_skills else "<none>"
            return CommandResult(output=f"available={available}\npinned={pinned}\nactive={active}")
        if args[0] == "clear":
            self.runtime_state.active_skills.clear()
            return CommandResult(output="Cleared pinned skills.")
        skill_id = args[0]
        try:
            await self.skill_registry.resolve(skill_id)
        except KeyError:
            return CommandResult(output=f"Unknown skill: {skill_id}", is_error=True)
        if skill_id in self.runtime_state.active_skills:
            self.runtime_state.active_skills.remove(skill_id)
            return CommandResult(output=f"Unpinned skill: {skill_id}")
        self.runtime_state.active_skills.append(skill_id)
        return CommandResult(output=f"Pinned skill: {skill_id}")

    async def _cmd_tag(self, args: list[str]) -> CommandResult:
        if not args:
            return CommandResult(output=f"Current task tag: {self.session.task_tag.value}")
        raw = args[0].lower()
        try:
            tag = TaskTag(raw)
        except ValueError:
            available = ", ".join(tag.value for tag in TaskTag)
            return CommandResult(output=f"Unknown task tag: {raw}. Available: {available}", is_error=True)
        self.session.task_tag = tag
        return CommandResult(output=f"Task tag set to: {tag.value}")

    async def _cmd_rate(self, args: list[str]) -> CommandResult:
        if not args:
            return CommandResult(output="Usage: /rate <1-5>", is_error=True)
        if self.session.last_turn_id is None:
            return CommandResult(output="No response is available to rate yet.", is_error=True)
        try:
            rating = int(args[0])
        except ValueError:
            return CommandResult(output="Rating must be an integer from 1 to 5.", is_error=True)
        if rating < 1 or rating > 5:
            return CommandResult(output="Rating must be between 1 and 5.", is_error=True)
        self.session.last_rating = rating
        await self.event_bus.publish(
            EventEnvelope.create(
                kind=EventKind.FEEDBACK_RECORDED,
                session_id=self.session.session_id,
                turn_id=self.session.last_turn_id,
                task_tag=self.session.task_tag,
                provider_id=self.runtime_state.active_provider,
                model_id=self.runtime_state.active_model,
                skill_ids=tuple(self.session.active_skills),
                payload={"rating": rating},
            )
        )
        return CommandResult(output=f"Recorded rating: {rating}")

    async def _cmd_ping(self, _: list[str]) -> CommandResult:
        snapshot = await self.health_service.refresh(force=True)
        text = "\n".join(f"{name}: {status.state.value} ({status.detail})" for name, status in sorted(snapshot.items()))
        return CommandResult(output=text or "No providers configured.")

    async def _cmd_add(self, args: list[str]) -> CommandResult:
        if not args:
            return CommandResult(output="Usage: /add <file...>", is_error=True)
        _, added = self.context_manager.add_files(self.session.active_files, args)
        self.runtime_state.active_files = list(self.session.active_files)
        if not added:
            return CommandResult(output="No files were added.", is_error=True)
        return CommandResult(output="Added files: " + ", ".join(added))

    async def _cmd_drop(self, args: list[str]) -> CommandResult:
        if not args:
            return CommandResult(output="Usage: /drop <file...>", is_error=True)
        _, removed = self.context_manager.drop_files(self.session.active_files, args)
        self.runtime_state.active_files = list(self.session.active_files)
        if not removed:
            return CommandResult(output="No files were removed.", is_error=True)
        return CommandResult(output="Removed files: " + ", ".join(removed))

    async def _cmd_clear(self, _: list[str]) -> CommandResult:
        self.session.active_files.clear()
        self.runtime_state.active_files.clear()
        self.runtime_state.manual_model_alias = None
        return CommandResult(output="Cleared active files and model pin.")

    async def _cmd_exit(self, _: list[str]) -> CommandResult:
        return CommandResult(output="Session finished.", should_exit=True)

    async def _request_approval_or_block(
        self,
        action: str,
        command: str,
        decision: PolicyDecision,
        *,
        metadata: dict[str, object] | None = None,
    ) -> CommandResult:
        payload = {
            "command": command,
            "action": decision.action.value,
            "risk_level": decision.risk_level.value,
            "reason": decision.reason,
            "safer_alternative": decision.safer_alternative,
        }
        approval_id = None
        if decision.action.value == "require_approval" and self.approval_manager is not None:
            approval = self.approval_manager.create(
                action=action,
                command=command,
                risk_level=decision.risk_level,
                reason=decision.reason,
                safer_alternative=decision.safer_alternative,
                metadata=dict(metadata or {}),
            )
            approval_id = approval.approval_id
            payload["approval_id"] = approval_id
        await self.event_bus.publish(
            EventEnvelope.create(
                kind=EventKind.POLICY_BLOCKED,
                session_id=self.session.session_id,
                task_tag=self.session.task_tag,
                payload=payload,
            )
        )
        message = decision.reason or "Command blocked by policy."
        if approval_id is not None:
            message += f"\nApproval required: {approval_id}"
            message += f"\nApprove with: /approve {approval_id}"
        if decision.safer_alternative:
            message += f"\nSafer alternative: {decision.safer_alternative}"
        return CommandResult(output=message, is_error=True)

    async def _execute_shell_command(
        self,
        command: str,
        decision: PolicyDecision,
        *,
        approved: bool = False,
        verify_after: bool = False,
    ) -> CommandResult:
        if self.tool_executor is None:
            return CommandResult(output="Execution layer is not configured.", is_error=True)
        sandbox = SandboxProfile.for_risk(decision.risk_level, approved=approved)
        await self.event_bus.publish(
            EventEnvelope.create(
                kind=EventKind.TOOL_CALLED,
                session_id=self.session.session_id,
                task_tag=self.session.task_tag,
                payload={
                    "command": command,
                    "tool_kind": "shell",
                    "sandbox": sandbox.name,
                    "approved": approved,
                },
            )
        )
        result = await self.tool_executor.run_shell(command, cwd=self.context_manager.project_root)
        await self.event_bus.publish(
            EventEnvelope.create(
                kind=EventKind.TOOL_FINISHED,
                session_id=self.session.session_id,
                task_tag=self.session.task_tag,
                payload={
                    "command": command,
                    "tool_kind": "shell",
                    "exit_code": result.exit_code,
                    "duration_ms": result.duration_ms,
                    "sandbox": sandbox.name,
                    "approved": approved,
                    **result.metadata,
                },
            )
        )
        rendered = [
            f"sandbox={sandbox.name}",
            f"exit_code={result.exit_code}",
            f"duration_ms={result.duration_ms if result.duration_ms is not None else '-'}",
        ]
        if result.stdout:
            rendered.append("stdout:\n" + result.stdout)
        if result.stderr:
            rendered.append("stderr:\n" + result.stderr)
        output = "\n".join(rendered)
        self._remember_tool_output(f"shell: {command}", output)
        if verify_after and self.verification_engine is not None and result.exit_code == 0:
            verification = await self._execute_verification(None, approved=approved, return_only=True)
            output = output + "\n\nverification:\n" + verification.summary
            if not verification.passed:
                self._remember_failure("verify", verification.checks_run[0] if verification.checks_run else "<default>", output)
                return CommandResult(output=output, is_error=True)
            self._clear_failure()
            return CommandResult(output=output)
        if result.exit_code != 0:
            self._remember_failure("run", command, output)
            return CommandResult(output=output, is_error=True)
        self._clear_failure()
        return CommandResult(output=output)

    async def _apply_replace(
        self,
        path: str,
        needle: str,
        replacement: str,
        *,
        verify_after: bool = False,
        approved: bool = False,
    ) -> CommandResult:
        if self.patch_service is None:
            return CommandResult(output="Patch service is not configured.", is_error=True)
        await self.event_bus.publish(
            EventEnvelope.create(
                kind=EventKind.PATCH_PROPOSED,
                session_id=self.session.session_id,
                task_tag=self.session.task_tag,
                payload={"path": path, "approved": approved, "verify_after": verify_after},
            )
        )
        try:
            patch = self.patch_service.replace_text(path, needle, replacement)
        except FileNotFoundError:
            message = f"File not found: {path}"
            self._remember_failure("replace", path, message)
            return CommandResult(output=message, is_error=True)
        except ValueError as exc:
            if str(exc) == "needle_not_found":
                message = f"Exact match not found in {path}."
            else:
                message = f"Replace is ambiguous in {path}; refine the old text to a unique match."
            self._remember_failure("replace", path, message)
            return CommandResult(output=message, is_error=True)

        await self.event_bus.publish(
            EventEnvelope.create(
                kind=EventKind.PATCH_APPLIED,
                session_id=self.session.session_id,
                task_tag=self.session.task_tag,
                payload={
                    "path": path,
                    "diff": patch.diff,
                    "backup_path": patch.backup_path,
                    "approved": approved,
                    "verify_after": verify_after,
                },
            )
        )
        if self.file_change_audit is not None:
            self.file_change_audit.record_patch(
                session_id=self.session.session_id,
                path=path,
                diff=patch.diff,
                backup_path=patch.backup_path,
                metadata={"approved": approved, "verify_after": verify_after},
            )
        self.session.recent_patches.append((path, patch.backup_path))
        if path not in self.session.active_files:
            self.session.active_files.append(path)
            self.runtime_state.active_files = list(self.session.active_files)

        rendered = [f"path={path}", "diff:\n" + patch.diff]
        self._remember_tool_output(f"patch: {path}", "\n".join(rendered))
        if verify_after and self.verification_engine is not None:
            verification = await self._execute_verification(None, approved=approved, return_only=True)
            rendered.append("verification:\n" + verification.summary)
            if not verification.passed:
                self._remember_failure("verify", verification.checks_run[0] if verification.checks_run else "<default>", "\n".join(rendered))
                return CommandResult(output="\n".join(rendered), is_error=True)
        self._clear_failure()
        return CommandResult(output="\n".join(rendered))

    async def _execute_verification(
        self,
        command: str | None,
        *,
        approved: bool = False,
        return_only: bool = False,
    ) -> CommandResult | VerificationResult:
        if self.verification_engine is None:
            result = VerificationResult(passed=False, summary="Verification engine is not configured.")
            return result if return_only else CommandResult(output=result.summary, is_error=True)
        verification = await self.verification_engine.verify(command)
        self.session.last_verification_summary = (
            ("passed: " if verification.passed else "failed: ") + summarize_output(verification.summary, max_chars=400).rendered
        )
        await self.event_bus.publish(
            EventEnvelope.create(
                kind=EventKind.VERIFICATION_FINISHED,
                session_id=self.session.session_id,
                task_tag=self.session.task_tag,
                payload={
                    "command": verification.checks_run[0] if verification.checks_run else command,
                    "passed": verification.passed,
                    "source": verification.metadata.get("source"),
                },
            )
        )
        rendered = [
            f"passed={verification.passed}",
            f"checks={', '.join(verification.checks_run) if verification.checks_run else '<none>'}",
            "summary:\n" + verification.summary,
        ]
        output = "\n".join(rendered)
        self._remember_tool_output("verification", output)
        if verification.passed:
            self._clear_failure()
        else:
            failed_command = verification.checks_run[0] if verification.checks_run else (command or "<default>")
            self._remember_failure("verify", failed_command, output)
        if return_only:
            return verification
        return CommandResult(output=output, is_error=not verification.passed)

    def _remember_tool_output(self, title: str, text: str, *, limit: int = 1200, keep: int = 4) -> None:
        summary = summarize_output(text, max_chars=limit).rendered
        if not summary:
            return
        block = f"{title}\n{summary}"
        self.session.recent_tool_outputs.append(block)
        if len(self.session.recent_tool_outputs) > keep:
            self.session.recent_tool_outputs[:] = self.session.recent_tool_outputs[-keep:]

    def _remember_failure(self, action: str, command: str, summary: str) -> None:
        self.session.last_failed_action = action
        self.session.last_failed_command = command
        self.session.last_failed_summary = summarize_output(summary, max_chars=800).rendered

    def _clear_failure(self) -> None:
        self.session.last_failed_action = None
        self.session.last_failed_command = None
        self.session.last_failed_summary = None

    def _find_patch_checkpoint(self, target: str) -> int | None:
        if target == "latest":
            return len(self.session.recent_patches) - 1
        for index in range(len(self.session.recent_patches) - 1, -1, -1):
            path, _ = self.session.recent_patches[index]
            if path == target:
                return index
        return None
