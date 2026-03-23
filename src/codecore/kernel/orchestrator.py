"""Main runtime orchestration loop."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..agents import MultiAgentRunner
from ..context.manager import ContextManager
from ..domain.contracts import ContextComposer, PolicyEngine, SkillRegistry, ToolExecutor, VerificationEngine
from ..domain.enums import EventKind, PolicyAction, RiskLevel, TaskTag
from ..domain.events import EventEnvelope
from ..domain.models import ChatMessage, ChatRequest
from ..execution.changesets import ChangeSet, ChangeSetApplier, ChangeSetEntry
from ..domain.results import PolicyDecision, VerificationResult
from ..execution.audit import FileChangeAudit
from ..execution.approvals import ApprovalManager
from ..execution.editing import EditOperation, EditPlan, StructuredEditParser
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

AUTOEDIT_SYSTEM_PROMPT = """Return only JSON with exact text replacements.
Schema:
{
  "edits": [
    {
      "path": "relative/path.py",
      "old": "exact existing text",
      "new": "replacement text",
      "reason": "short explanation"
    }
  ]
}
Rules:
- edit only active files provided in context
- each file may appear at most once
- use exact snippets that exist exactly once
- do not include markdown, prose, or code fences unless the entire response is a json code fence
"""


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
    multi_agent_runner: MultiAgentRunner | None = None
    tool_executor: ToolExecutor | None = None
    policy_engine: PolicyEngine | None = None
    git_workspace: GitWorkspace | None = None
    patch_service: PatchService | None = None
    file_change_audit: FileChangeAudit | None = None
    approval_manager: ApprovalManager | None = None
    verification_engine: VerificationEngine | None = None
    edit_parser: StructuredEditParser = field(default_factory=StructuredEditParser)
    command_router: CommandRouter = field(init=False)

    def __post_init__(self) -> None:
        self.command_router = CommandRouter()
        self.command_router.register("help", self._cmd_help)
        self.command_router.register("status", self._cmd_status)
        self.command_router.register("stats", self._cmd_stats)
        self.command_router.register("pipelines", self._cmd_pipelines)
        self.command_router.register("delegate", self._cmd_delegate)
        self.command_router.register("benchmark", self._cmd_benchmark)
        self.command_router.register("run", self._cmd_run)
        self.command_router.register("autoedit", self._cmd_autoedit)
        self.command_router.register("replace", self._cmd_replace)
        self.command_router.register("rollback", self._cmd_rollback)
        self.command_router.register("retry", self._cmd_retry)
        self.command_router.register("approvals", self._cmd_approvals)
        self.command_router.register("approve", self._cmd_approve)
        self.command_router.register("dismiss", self._cmd_dismiss)
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
        self._update_context_metrics(request)
        return await self._invoke_request(prompt, request, turn_id=turn.turn_id)

    async def _invoke_request(self, prompt: str, request: ChatRequest, *, turn_id: str) -> CommandResult:
        if self.session.active_skills:
            await self.event_bus.publish(
                EventEnvelope.create(
                    kind=EventKind.SKILL_ACTIVATED,
                    session_id=self.session.session_id,
                    turn_id=turn_id,
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
                    turn_id=turn_id,
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
                            turn_id=turn_id,
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
            self.session.last_turn_id = turn_id
            await self.event_bus.publish(
                EventEnvelope.create(
                    kind=EventKind.MODEL_INVOKED,
                    session_id=self.session.session_id,
                    turn_id=turn_id,
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
            return CommandResult(output=result.text, render_mode="markdown")

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
            f"context_files={self.session.last_context_file_count}\n"
            f"context_tokens={self.session.last_context_token_count}\n"
            f"active_skills={active_skills}\n"
            f"pinned_skills={pinned_skills}\n"
            f"allowed_approval_types={', '.join(self.session.allowed_action_types) if self.session.allowed_action_types else '<none>'}\n"
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

    async def _cmd_pipelines(self, _: list[str]) -> CommandResult:
        if self.multi_agent_runner is None:
            return CommandResult(output="Multi-agent runner is not configured.", is_error=True)
        current = self.runtime_state.active_pipeline or "<none>"
        lines = [f"active_pipeline={current}"]
        for pipeline in self.multi_agent_runner.list_pipelines():
            roles = " -> ".join(role.value for role in pipeline.roles)
            lines.append(f"{pipeline.pipeline_id}: {roles} | {pipeline.description}")
        return CommandResult(output="\n".join(lines))

    async def _cmd_delegate(self, args: list[str]) -> CommandResult:
        if self.multi_agent_runner is None:
            return CommandResult(output="Multi-agent runner is not configured.", is_error=True)
        if not args:
            return CommandResult(output="Usage: /delegate [--pipeline <id>] [--verify] [--apply] <instruction>", is_error=True)
        verify_requested = False
        apply_requested = False
        pipeline_hint: str | None = None
        index = 0
        while index < len(args):
            token = args[index]
            if token == "--verify":
                verify_requested = True
                index += 1
                continue
            if token == "--apply":
                apply_requested = True
                index += 1
                continue
            if token == "--pipeline":
                if index + 1 >= len(args):
                    return CommandResult(output="Usage: /delegate [--pipeline <id>] [--verify] [--apply] <instruction>", is_error=True)
                pipeline_hint = args[index + 1]
                index += 2
                continue
            break
        instruction = " ".join(args[index:]).strip()
        if not instruction:
            return CommandResult(output="Usage: /delegate [--pipeline <id>] [--verify] [--apply] <instruction>", is_error=True)
        if not self.session.active_files:
            return CommandResult(output="Delegate requires active files. Use /add first.", is_error=True)
        try:
            result = await self.multi_agent_runner.run(
                instruction=instruction,
                active_files=tuple(self.session.active_files),
                task_tag=self.session.task_tag,
                pipeline_hint=pipeline_hint,
                verify_requested=verify_requested,
            )
        except (KeyError, RuntimeError, ValueError) as exc:
            self._remember_failure("delegate", instruction, str(exc))
            return CommandResult(output=str(exc), is_error=True)
        self.runtime_state.active_pipeline = result.pipeline_id
        is_error = bool(result.review is not None and not result.review.approved)
        if result.evaluation is not None and result.evaluation.status == "failed":
            is_error = True
        if apply_requested:
            if result.change_set is None or result.change_set.is_empty():
                return CommandResult(
                    output=result.summary + "\n\nNo isolated change set is available for apply-back.",
                    is_error=True,
                )
            if not result.merge_ready:
                return CommandResult(
                    output=result.summary + "\n\nApply-back is unavailable because review or evaluation did not approve the change set.",
                    is_error=True,
                )
            if self.approval_manager is None or self.patch_service is None:
                return CommandResult(output="Apply-back is not configured.", is_error=True)
            decision = PolicyDecision(
                action=PolicyAction.REQUIRE_APPROVAL,
                risk_level=RiskLevel.WORKSPACE_WRITE,
                reason=f"Applying {len(result.change_set.entries)} change-set file(s) will mutate the main workspace.",
                safer_alternative="Inspect the isolated workspace diff before approving apply-back.",
            )
            if self._is_action_type_allowed("delegate-apply"):
                apply_result = await self._apply_delegate_change_set(result.change_set, approved=True)
                return CommandResult(output=result.summary + "\n\n" + apply_result.output, is_error=apply_result.is_error)
            approval = await self._request_approval_or_block(
                "delegate-apply",
                f"delegate apply {instruction}",
                decision,
                metadata=self._serialize_change_set(result.change_set),
            )
            return CommandResult(output=result.summary + "\n\n" + approval.output, is_error=approval.is_error)
        return CommandResult(output=result.summary, is_error=is_error)

    async def _cmd_benchmark(self, args: list[str]) -> CommandResult:
        if self.multi_agent_runner is None:
            return CommandResult(output="Multi-agent runner is not configured.", is_error=True)
        if not args:
            return CommandResult(
                output="Usage: /benchmark [--models a,b] [--pipeline <id>] [--verify] <instruction>",
                is_error=True,
            )
        verify_requested = False
        pipeline_hint: str | None = None
        model_aliases: tuple[str, ...] = ()
        index = 0
        while index < len(args):
            token = args[index]
            if token == "--verify":
                verify_requested = True
                index += 1
                continue
            if token == "--pipeline":
                if index + 1 >= len(args):
                    return CommandResult(
                        output="Usage: /benchmark [--models a,b] [--pipeline <id>] [--verify] <instruction>",
                        is_error=True,
                    )
                pipeline_hint = args[index + 1]
                index += 2
                continue
            if token == "--models":
                if index + 1 >= len(args):
                    return CommandResult(
                        output="Usage: /benchmark [--models a,b] [--pipeline <id>] [--verify] <instruction>",
                        is_error=True,
                    )
                model_aliases = tuple(alias.strip() for alias in args[index + 1].split(",") if alias.strip())
                index += 2
                continue
            break
        instruction = " ".join(args[index:]).strip()
        if not instruction:
            return CommandResult(
                output="Usage: /benchmark [--models a,b] [--pipeline <id>] [--verify] <instruction>",
                is_error=True,
            )
        if not self.session.active_files:
            return CommandResult(output="Benchmark requires active files. Use /add first.", is_error=True)
        results = await self.multi_agent_runner.benchmark(
            instruction=instruction,
            active_files=tuple(self.session.active_files),
            task_tag=self.session.task_tag,
            model_aliases=model_aliases,
            pipeline_hint=pipeline_hint,
            verify_requested=verify_requested,
        )
        lines = [f"benchmark_models={len(results)}"]
        for item in results:
            status = "ok" if item.success else "failed"
            lines.append(
                f"{item.model_alias} | pipeline={item.pipeline_id} | status={status} | evaluation={item.evaluation_status} | review={item.review_status} | retries={item.retry_count} | edits={item.edit_count}"
            )
            if item.error:
                lines.append(f"error[{item.model_alias}]={item.error}")
        return CommandResult(output="\n".join(lines))

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
            if self._is_action_type_allowed("run"):
                return await self._execute_shell_command(command, decision, approved=True, verify_after=verify_after)
            return await self._request_approval_or_block("run", command, decision)
        return await self._execute_shell_command(command, decision, verify_after=verify_after)

    async def _cmd_autoedit(self, args: list[str]) -> CommandResult:
        if not args:
            return CommandResult(output="Usage: /autoedit [--verify] <instruction>", is_error=True)
        if not self.session.active_files:
            return CommandResult(output="Autoedit requires active files. Use /add first.", is_error=True)
        if self.approval_manager is None:
            return CommandResult(output="Approval manager is not configured.", is_error=True)

        verify_after = False
        if args and args[0] == "--verify":
            verify_after = True
            args = args[1:]
        if not args:
            return CommandResult(output="Usage: /autoedit [--verify] <instruction>", is_error=True)

        instruction = " ".join(args)
        turn = new_turn_context(f"/autoedit {instruction}")
        request = ChatRequest(
            messages=(
                ChatMessage(
                    role="user",
                    content=self._build_autoedit_prompt(instruction),
                ),
            ),
            system_prompt=AUTOEDIT_SYSTEM_PROMPT,
            task_tag=self.session.task_tag,
            model_hint=self.runtime_state.manual_model_alias,
            max_output_tokens=1200,
            metadata={"mode": "autoedit"},
        )
        request = await self.context_composer.compose(request)
        result = await self._invoke_request(f"autoedit: {instruction}", request, turn_id=turn.turn_id)
        if result.is_error:
            return result
        raw_response = result.output or ""
        try:
            plan = self.edit_parser.parse(raw_response, allowed_paths=tuple(self.session.active_files))
        except ValueError as exc:
            message = f"Model edit plan is invalid: {exc}\nRaw response:\n{summarize_output(raw_response, max_chars=800).rendered}"
            self._remember_failure("autoedit", instruction, message)
            return CommandResult(output=message, is_error=True)

        decision = PolicyDecision(
            action=PolicyAction.REQUIRE_APPROVAL,
            risk_level=RiskLevel.WORKSPACE_WRITE,
            reason=f"Applying {len(plan.edits)} model-generated edit(s) mutates workspace files.",
            safer_alternative="Inspect the proposed diff summary before approving the edit plan.",
        )
        if self._is_action_type_allowed("autoedit"):
            return await self._apply_edit_plan(tuple(plan.edits), verify_after=verify_after, approved=True)
        approval = await self._request_approval_or_block(
            "autoedit",
            f"autoedit {instruction}",
            decision,
            metadata={
                "verify_after": verify_after,
                "edits": [
                    {"path": item.path, "old": item.old, "new": item.new, "reason": item.reason}
                    for item in plan.edits
                ],
            },
        )
        summary = self._render_edit_plan(plan)
        return CommandResult(output=summary + "\n\n" + approval.output, is_error=approval.is_error)

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
        if self._is_action_type_allowed("replace"):
            return await self._apply_replace(path, needle, replacement, verify_after=verify_after, approved=True)
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
        for index, item in enumerate(pending, start=1):
            lines.append(
                f"{index}. {item.approval_id} | {item.action} | {item.risk_level.value} | {self._summarize_command(item.command)}"
            )
            lines.append("   1 allow once: /approve " + item.approval_id)
            lines.append("   2 allow this type: /approve 2")
            lines.append("   3 dismiss: /dismiss " + item.approval_id)
        return CommandResult(output="\n".join(lines))

    async def _cmd_approve(self, args: list[str]) -> CommandResult:
        if not args:
            return CommandResult(output="Usage: /approve <approval-id|latest|1|2>", is_error=True)
        if self.approval_manager is None:
            return CommandResult(output="Approval manager is not configured.", is_error=True)
        approval_id = args[0]
        allow_type = False
        if approval_id in {"1", "latest"}:
            approval = self.approval_manager.latest()
            if approval is None:
                return CommandResult(output="No pending approvals.", is_error=True)
            approval_id = approval.approval_id
        elif approval_id == "2":
            approval = self.approval_manager.latest()
            if approval is None:
                return CommandResult(output="No pending approvals.", is_error=True)
            approval_id = approval.approval_id
            allow_type = True
        approval = self.approval_manager.resolve(approval_id)
        if approval is None:
            return CommandResult(output=f"Unknown approval id: {approval_id}", is_error=True)
        prefix = ""
        if allow_type:
            self._allow_action_type(approval.action)
            prefix = f"Approved action type for this session: {approval.action}\n"
        decision = PolicyDecision(
            action=PolicyAction.ALLOW,
            risk_level=approval.risk_level,
            reason=approval.reason,
            safer_alternative=approval.safer_alternative,
        )
        if approval.action == "run":
            result = await self._execute_shell_command(approval.command, decision, approved=True)
            return self._prepend_output(prefix, result)
        if approval.action == "replace":
            path = approval.metadata.get("path")
            needle = approval.metadata.get("needle")
            replacement = approval.metadata.get("replacement")
            if not isinstance(path, str) or not isinstance(needle, str) or not isinstance(replacement, str):
                return CommandResult(output="Approval payload for replace is invalid.", is_error=True)
            result = await self._apply_replace(
                path,
                needle,
                replacement,
                verify_after=bool(approval.metadata.get("verify_after")),
                approved=True,
            )
            return self._prepend_output(prefix, result)
        if approval.action == "autoedit":
            raw_edits = approval.metadata.get("edits")
            if not isinstance(raw_edits, list):
                return CommandResult(output="Approval payload for autoedit is invalid.", is_error=True)
            edits: list[EditOperation] = []
            for item in raw_edits:
                if not isinstance(item, dict):
                    return CommandResult(output="Approval payload for autoedit is invalid.", is_error=True)
                path = item.get("path")
                old = item.get("old")
                new = item.get("new")
                reason = item.get("reason", "")
                if not isinstance(path, str) or not isinstance(old, str) or not isinstance(new, str) or not isinstance(reason, str):
                    return CommandResult(output="Approval payload for autoedit is invalid.", is_error=True)
                edits.append(EditOperation(path=path, old=old, new=new, reason=reason))
            result = await self._apply_edit_plan(
                tuple(edits),
                verify_after=bool(approval.metadata.get("verify_after")),
                approved=True,
            )
            return self._prepend_output(prefix, result)
        if approval.action == "delegate-apply":
            try:
                change_set = self._deserialize_change_set(approval.metadata)
            except ValueError as exc:
                return CommandResult(output=f"Approval payload for delegate apply is invalid: {exc}", is_error=True)
            result = await self._apply_delegate_change_set(change_set, approved=True)
            return self._prepend_output(prefix, result)
        if approval.action == "verify":
            result = await self._execute_verification(approval.command or None, approved=True)
            return self._prepend_output(prefix, result)
        return CommandResult(output=f"Unsupported approval action: {approval.action}", is_error=True)

    async def _cmd_dismiss(self, args: list[str]) -> CommandResult:
        if self.approval_manager is None:
            return CommandResult(output="Approval manager is not configured.", is_error=True)
        approval_id = args[0] if args else "latest"
        if approval_id in {"3", "latest"}:
            approval = self.approval_manager.latest()
            if approval is None:
                return CommandResult(output="No pending approvals.", is_error=True)
            approval_id = approval.approval_id
        dismissed = self.approval_manager.dismiss(approval_id)
        if dismissed is None:
            return CommandResult(output=f"Unknown approval id: {approval_id}", is_error=True)
        return CommandResult(output=f"Dismissed approval: {dismissed.approval_id} ({dismissed.action})")

    async def _cmd_verify(self, args: list[str]) -> CommandResult:
        if self.verification_engine is None:
            return CommandResult(output="Verification engine is not configured.", is_error=True)
        command = " ".join(args) if args else None
        if command and self.policy_engine is not None:
            decision = await self.policy_engine.evaluate_tool_call(command)
            if decision.action.value != "allow":
                if self._is_action_type_allowed("verify"):
                    return await self._execute_verification(command, approved=True)
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
            message += "\n1. allow once: /approve 1"
            message += "\n2. allow this type: /approve 2"
            message += "\n3. dismiss: /dismiss 3"
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

    async def _apply_edit_plan(
        self,
        edits: tuple[EditOperation, ...],
        *,
        verify_after: bool = False,
        approved: bool = False,
    ) -> CommandResult:
        if self.patch_service is None:
            return CommandResult(output="Patch service is not configured.", is_error=True)
        rendered = [f"applied_edits={len(edits)}"]
        applied: list[tuple[EditOperation, str | None]] = []
        for edit in edits:
            await self.event_bus.publish(
                EventEnvelope.create(
                    kind=EventKind.PATCH_PROPOSED,
                    session_id=self.session.session_id,
                    task_tag=self.session.task_tag,
                    payload={"path": edit.path, "approved": approved, "mode": "autoedit", "reason": edit.reason},
                )
            )
            try:
                patch = self.patch_service.replace_text(edit.path, edit.old, edit.new)
            except (FileNotFoundError, ValueError) as exc:
                for applied_edit, backup_path in reversed(applied):
                    self.patch_service.undo(applied_edit.path, backup_path)
                if applied and self.file_change_audit is not None:
                    self.file_change_audit.record_restore(
                        session_id=self.session.session_id,
                        paths=tuple(item.path for item, _ in applied),
                        metadata={"source": "autoedit.partial-rollback"},
                    )
                cause = self._format_patch_failure(edit.path, exc)
                message = f"Autoedit apply failed. {cause}"
                if applied:
                    message += f"\nRolled back {len(applied)} already applied edit(s)."
                self._remember_failure("autoedit", edit.path, message)
                return CommandResult(output=message, is_error=True)

            await self.event_bus.publish(
                EventEnvelope.create(
                    kind=EventKind.PATCH_APPLIED,
                    session_id=self.session.session_id,
                    task_tag=self.session.task_tag,
                    payload={
                        "path": edit.path,
                        "diff": patch.diff,
                        "backup_path": patch.backup_path,
                        "approved": approved,
                        "mode": "autoedit",
                        "reason": edit.reason,
                    },
                )
            )
            if self.file_change_audit is not None:
                self.file_change_audit.record_patch(
                    session_id=self.session.session_id,
                    path=edit.path,
                    diff=patch.diff,
                    backup_path=patch.backup_path,
                    metadata={"approved": approved, "mode": "autoedit", "reason": edit.reason},
                )
            self.session.recent_patches.append((edit.path, patch.backup_path))
            applied.append((edit, patch.backup_path))
            if edit.path not in self.session.active_files:
                self.session.active_files.append(edit.path)
                self.runtime_state.active_files = list(self.session.active_files)
            diff_summary = summarize_output(patch.diff, max_chars=700).rendered
            label = f"{edit.path}: {edit.reason}" if edit.reason else edit.path
            rendered.append(label + "\n" + diff_summary)

        self._remember_tool_output("autoedit plan", "\n\n".join(rendered))
        if verify_after and self.verification_engine is not None:
            verification = await self._execute_verification(None, approved=approved, return_only=True)
            rendered.append("verification:\n" + verification.summary)
            if not verification.passed:
                self._remember_failure("verify", verification.checks_run[0] if verification.checks_run else "<default>", "\n".join(rendered))
                return CommandResult(output="\n\n".join(rendered), is_error=True)

        self._clear_failure()
        return CommandResult(output="\n\n".join(rendered))

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

    async def _apply_delegate_change_set(self, change_set: ChangeSet, *, approved: bool = False) -> CommandResult:
        if self.patch_service is None:
            return CommandResult(output="Patch service is not configured.", is_error=True)
        await self.event_bus.publish(
            EventEnvelope.create(
                kind=EventKind.TOOL_CALLED,
                session_id=self.session.session_id,
                task_tag=self.session.task_tag,
                payload={
                    "command": "delegate-apply",
                    "tool_kind": "merge",
                    "paths": change_set.paths(),
                    "approved": approved,
                    "source_workspace": change_set.source_workspace,
                },
            )
        )
        try:
            result = ChangeSetApplier(self.patch_service).apply(change_set)
        except RuntimeError as exc:
            self._remember_failure("delegate-apply", ", ".join(change_set.paths()), str(exc))
            return CommandResult(output=str(exc), is_error=True)
        if result.conflicts:
            output = "Apply-back aborted due to conflicts in: " + ", ".join(result.conflicts)
            self._remember_failure("delegate-apply", ", ".join(change_set.paths()), output)
            await self.event_bus.publish(
                EventEnvelope.create(
                    kind=EventKind.TOOL_FINISHED,
                    session_id=self.session.session_id,
                    task_tag=self.session.task_tag,
                    payload={
                        "command": "delegate-apply",
                        "tool_kind": "merge",
                        "approved": approved,
                        "conflicts": result.conflicts,
                        "source_workspace": change_set.source_workspace,
                    },
                )
            )
            return CommandResult(output=output, is_error=True)

        for application in result.applications:
            await self.event_bus.publish(
                EventEnvelope.create(
                    kind=EventKind.PATCH_APPLIED,
                    session_id=self.session.session_id,
                    task_tag=self.session.task_tag,
                    payload={
                        "path": application.path,
                        "diff": application.diff,
                        "backup_path": application.backup_path,
                        "approved": approved,
                        "mode": "delegate-apply",
                        "source_workspace": change_set.source_workspace,
                    },
                )
            )
            if self.file_change_audit is not None:
                self.file_change_audit.record_patch(
                    session_id=self.session.session_id,
                    path=application.path,
                    diff=application.diff,
                    backup_path=application.backup_path,
                    metadata={"approved": approved, "mode": "delegate-apply", "source_workspace": change_set.source_workspace},
                )
            self.session.recent_patches.append((application.path, application.backup_path))
            if application.path not in self.session.active_files:
                self.session.active_files.append(application.path)
                self.runtime_state.active_files = list(self.session.active_files)
        await self.event_bus.publish(
            EventEnvelope.create(
                kind=EventKind.TOOL_FINISHED,
                session_id=self.session.session_id,
                task_tag=self.session.task_tag,
                payload={
                    "command": "delegate-apply",
                    "tool_kind": "merge",
                    "approved": approved,
                    "paths": result.applied_files,
                    "source_workspace": change_set.source_workspace,
                },
            )
        )
        lines = [
            f"applied_change_set={len(result.applied_files)}",
            f"source_workspace={change_set.source_workspace}",
            f"target_workspace={change_set.target_workspace}",
            "diff:\n" + result.diff_summary,
        ]
        output = "\n".join(lines)
        self._remember_tool_output("delegate apply", output)
        self._clear_failure()
        return CommandResult(output=output)

    def _remember_tool_output(self, title: str, text: str, *, limit: int = 1200, keep: int = 4) -> None:
        summary = summarize_output(text, max_chars=limit).rendered
        if not summary:
            return
        block = f"{title}\n{summary}"
        self.session.recent_tool_outputs.append(block)
        if len(self.session.recent_tool_outputs) > keep:
            self.session.recent_tool_outputs[:] = self.session.recent_tool_outputs[-keep:]

    def _update_context_metrics(self, request: ChatRequest) -> None:
        reports = request.metadata.get("selected_context_reports", [])
        if not isinstance(reports, list):
            self.session.last_context_file_count = 0
            self.session.last_context_token_count = 0
            return
        token_count = 0
        for item in reports:
            if isinstance(item, dict):
                value = item.get("selected_tokens")
                if isinstance(value, int):
                    token_count += value
        self.session.last_context_file_count = len(reports)
        self.session.last_context_token_count = token_count

    def _is_action_type_allowed(self, action: str) -> bool:
        return action in self.session.allowed_action_types

    def _allow_action_type(self, action: str) -> None:
        if action not in self.session.allowed_action_types:
            self.session.allowed_action_types.append(action)

    @staticmethod
    def _prepend_output(prefix: str, result: CommandResult) -> CommandResult:
        if not prefix:
            return result
        return CommandResult(
            output=prefix + result.output,
            should_exit=result.should_exit,
            is_error=result.is_error,
            render_mode=result.render_mode,
        )

    @staticmethod
    def _summarize_command(command: str, *, limit: int = 96) -> str:
        compact = " ".join(command.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3] + "..."

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

    def _build_autoedit_prompt(self, instruction: str) -> str:
        active_files = "\n".join(f"- {path}" for path in self.session.active_files)
        return (
            f"Task: {instruction}\n"
            f"Active files allowed for editing:\n{active_files}\n\n"
            "Return only a structured edit plan in JSON."
        )

    def _serialize_change_set(self, change_set: ChangeSet) -> dict[str, object]:
        return {
            "source_workspace": change_set.source_workspace,
            "target_workspace": change_set.target_workspace,
            "entries": [
                {
                    "path": entry.path,
                    "before": entry.before,
                    "after": entry.after,
                    "diff": entry.diff,
                }
                for entry in change_set.entries
            ],
        }

    def _deserialize_change_set(self, payload: dict[str, object]) -> ChangeSet:
        source_workspace = payload.get("source_workspace")
        target_workspace = payload.get("target_workspace")
        raw_entries = payload.get("entries")
        if not isinstance(source_workspace, str) or not isinstance(target_workspace, str) or not isinstance(raw_entries, list):
            raise ValueError("missing source/target workspace or entries")
        entries: list[ChangeSetEntry] = []
        for item in raw_entries:
            if not isinstance(item, dict):
                raise ValueError("entries must be objects")
            path = item.get("path")
            before = item.get("before")
            after = item.get("after")
            diff = item.get("diff")
            if not all(isinstance(value, str) for value in (path, before, after, diff)):
                raise ValueError("change-set entry contains invalid fields")
            entries.append(ChangeSetEntry(path=path, before=before, after=after, diff=diff))
        return ChangeSet(source_workspace=source_workspace, target_workspace=target_workspace, entries=tuple(entries))

    def _render_edit_plan(self, plan: EditPlan) -> str:
        lines = [f"planned_edits={len(plan.edits)}"]
        for item in plan.edits:
            reason = f" ({item.reason})" if item.reason else ""
            lines.append(f"- {item.path}{reason}")
        return "\n".join(lines)

    def _format_patch_failure(self, path: str, exc: Exception) -> str:
        if isinstance(exc, FileNotFoundError):
            return f"File not found: {path}"
        if str(exc) == "needle_not_found":
            return f"Exact match not found in {path}."
        if str(exc) == "needle_ambiguous":
            return f"Edit is ambiguous in {path}; model selected a non-unique snippet."
        return f"Patch application failed for {path}: {exc}"
