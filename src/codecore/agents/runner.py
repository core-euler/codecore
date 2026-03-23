"""Runtime orchestration for multi-agent pipelines."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from ..context.manager import ContextManager
from ..domain.enums import EventKind, TaskTag
from ..domain.events import EventEnvelope
from ..execution.changesets import ChangeSet, ChangeSetApplier, ChangeSetBuilder
from ..execution.files import WorkspaceFiles
from ..execution.git import GitWorkspace
from ..execution.patches import PatchService
from ..execution.tests import VerificationRunner
from ..execution.worktrees import WorktreeHandle, WorktreeManager
from ..kernel.event_bus import EventBus
from ..kernel.runtime_state import RuntimeState
from ..kernel.session import SessionRuntime
from ..providers.adapters.base import AdapterFactory
from ..providers.broker import BrokerError, PolicyDrivenBroker
from ..providers.health import ProviderHealthService
from .classifier import TaskClassifier
from .coder import CoderAgent
from .evaluator import EvaluatorAgent
from .models import AgentRole, BenchmarkResult, CoderOutput, PipelineDefinition, WorkflowResult
from .pipelines import PipelineRegistry
from .planner import PlannerAgent
from .reviewer import ReviewerAgent
from .synthesizer import SynthesizerAgent


class MultiAgentRunner:
    def __init__(
        self,
        *,
        project_root: Path,
        artifact_dir: Path,
        session: SessionRuntime,
        runtime_state: RuntimeState,
        broker: PolicyDrivenBroker,
        health_service: ProviderHealthService,
        adapter_factory: AdapterFactory,
        event_bus: EventBus,
        task_classifier: TaskClassifier | None = None,
        planner: PlannerAgent | None = None,
        coder: CoderAgent | None = None,
        reviewer: ReviewerAgent | None = None,
        evaluator: EvaluatorAgent | None = None,
        synthesizer: SynthesizerAgent | None = None,
        pipeline_registry: PipelineRegistry | None = None,
        worktree_manager: WorktreeManager | None = None,
    ) -> None:
        self._project_root = project_root.resolve()
        self._artifact_dir = artifact_dir.resolve()
        self._session = session
        self._runtime_state = runtime_state
        self._broker = broker
        self._health_service = health_service
        self._provider_registry = getattr(broker, "_registry", None) or getattr(health_service, "_registry", None)
        self._adapter_factory = adapter_factory
        self._event_bus = event_bus
        self._classifier = task_classifier or TaskClassifier()
        self._planner = planner or PlannerAgent()
        self._coder = coder or CoderAgent()
        self._reviewer = reviewer or ReviewerAgent()
        self._evaluator = evaluator or EvaluatorAgent(
            verification_runner_factory=lambda root: VerificationRunner(self._tool_executor(), root)
        )
        self._synthesizer = synthesizer or SynthesizerAgent()
        self._pipelines = pipeline_registry or PipelineRegistry()
        self._worktrees = worktree_manager or WorktreeManager(self._project_root, self._artifact_dir / "worktrees")

    def list_pipelines(self) -> tuple[PipelineDefinition, ...]:
        return self._pipelines.list()

    async def benchmark(
        self,
        *,
        instruction: str,
        active_files: tuple[str, ...],
        task_tag: TaskTag,
        model_aliases: tuple[str, ...] = (),
        pipeline_hint: str | None = None,
        verify_requested: bool = False,
    ) -> tuple[BenchmarkResult, ...]:
        aliases = model_aliases or await self._default_benchmark_aliases()
        original_model_hint = self._runtime_state.manual_model_alias
        results: list[BenchmarkResult] = []
        for alias in aliases:
            try:
                workflow = await self.run(
                    instruction=instruction,
                    active_files=active_files,
                    task_tag=task_tag,
                    pipeline_hint=pipeline_hint,
                    verify_requested=verify_requested,
                    model_hint=alias,
                )
            except Exception as exc:
                results.append(
                    BenchmarkResult(
                        model_alias=alias,
                        pipeline_id=pipeline_hint or "<auto>",
                        success=False,
                        error=str(exc),
                        summary=str(exc),
                    )
                )
                continue
            results.append(
                BenchmarkResult(
                    model_alias=alias,
                    pipeline_id=workflow.pipeline_id,
                    success=not (
                        (workflow.review is not None and not workflow.review.approved)
                        or (workflow.evaluation is not None and workflow.evaluation.status == "failed")
                    ),
                    evaluation_status=workflow.evaluation.status if workflow.evaluation is not None else "skipped",
                    review_status=(
                        "approved" if workflow.review is not None and workflow.review.approved else
                        "rejected" if workflow.review is not None else
                        "skipped"
                    ),
                    retry_count=workflow.retry_count,
                    edit_count=workflow.coding.edit_count,
                    summary=workflow.summary,
                )
            )
        self._runtime_state.manual_model_alias = original_model_hint
        return tuple(results)

    async def run(
        self,
        *,
        instruction: str,
        active_files: tuple[str, ...],
        task_tag: TaskTag,
        pipeline_hint: str | None = None,
        verify_requested: bool = False,
        model_hint: str | None = None,
    ) -> WorkflowResult:
        classification = self._classifier.classify(instruction, task_tag=task_tag, active_files=active_files)
        pipeline = self._pipelines.get(pipeline_hint or classification.pipeline_id)
        self._runtime_state.active_pipeline = pipeline.pipeline_id
        await self._event_bus.publish(
            EventEnvelope.create(
                kind=EventKind.TASK_CLASSIFIED,
                session_id=self._session.session_id,
                task_tag=task_tag,
                pipeline_id=pipeline.pipeline_id,
                payload={"reason": classification.reason, "complexity": classification.complexity},
            )
        )
        await self._event_bus.publish(
            EventEnvelope.create(
                kind=EventKind.PIPELINE_SELECTED,
                session_id=self._session.session_id,
                task_tag=task_tag,
                pipeline_id=pipeline.pipeline_id,
                payload={"roles": [role.value for role in pipeline.roles]},
            )
        )

        plan = self._planner.plan(instruction, active_files, pipeline_id=pipeline.pipeline_id)
        run_id = str(uuid4())[:8]
        coder_workspace = self._project_root
        coder_worktree: WorktreeHandle | None = None
        isolated = False
        if AgentRole.CODER in pipeline.isolated_roles and self._worktrees.is_supported():
            coder_worktree = self._worktrees.create(f"{run_id}-coder")
            coder_workspace = coder_worktree.path
            isolated = True
            self._sync_active_files_to_workspace(active_files, coder_workspace)

        context_manager = ContextManager(coder_workspace)
        max_coder_attempts = 2 if (verify_requested or AgentRole.EVALUATOR in pipeline.roles) else 1
        retries_used = 0
        coding: CoderOutput | None = None
        change_set: ChangeSet | None = None
        evaluation = None
        review_workspace = coder_workspace
        reviewer_worktree: WorktreeHandle | None = None
        failure_summary = ""
        while True:
            coder_attempt = retries_used + 1
            attempt_instruction = self._retry_instruction(instruction, failure_summary, coder_attempt)
            model_response = await self._invoke_coder(
                attempt_instruction,
                active_files,
                context_manager,
                plan,
                task_tag,
                pipeline.pipeline_id,
                coder_attempt=coder_attempt,
                model_hint=model_hint,
            )
            edit_plan = self._coder.plan_edits(
                instruction=attempt_instruction,
                active_files=active_files,
                context_manager=context_manager,
                model_response=model_response,
            )
            coding = self._apply_edit_plan(edit_plan, coder_workspace, run_id, isolated)
            change_set = self._build_change_set(
                tuple(coding.applied_files),
                coder_workspace,
                run_id,
                isolated=isolation_enabled(isolated, coder_worktree),
            )
            review_workspace, reviewer_worktree = self._prepare_review_workspace(
                pipeline=pipeline,
                change_set=change_set,
                coder_workspace=coder_workspace,
                active_files=active_files,
                run_id=run_id,
                attempt=coder_attempt,
            )

            evaluation = None
            evaluation_workspace = review_workspace if AgentRole.REVIEWER in pipeline.roles else coder_workspace
            if verify_requested or AgentRole.EVALUATOR in pipeline.roles:
                evaluation = await self._evaluator.evaluate(evaluation_workspace)
            if evaluation is None or evaluation.status != "failed" or coder_attempt >= max_coder_attempts:
                break
            retries_used += 1
            failure_summary = evaluation.summary

        if coding is None:
            raise RuntimeError("Coder pipeline produced no output.")
        review = None
        if AgentRole.REVIEWER in pipeline.roles:
            review_diff = GitWorkspace(review_workspace).diff_summary(change_set.paths() if change_set is not None else tuple(coding.applied_files))
            review = self._reviewer.review(
                diff_summary=review_diff,
                evaluation=evaluation,
                applied_files=coding.applied_files,
            )
        merge_ready = bool(
            change_set is not None
            and not change_set.is_empty()
            and (review is None or review.approved)
            and (evaluation is None or evaluation.status != "failed")
        )
        result = WorkflowResult(
            pipeline_id=pipeline.pipeline_id,
            classification=classification,
            plan=plan,
            coding=coding,
            review=review,
            evaluation=evaluation,
            workspace_path=str(coder_workspace),
            review_workspace_path=str(review_workspace) if review_workspace != coder_workspace else None,
            isolated=isolation_enabled(isolated, coder_worktree),
            retry_count=retries_used,
            merge_ready=merge_ready,
            change_set=change_set,
        )
        summary = self._synthesizer.summarize(result)
        return WorkflowResult(
            pipeline_id=result.pipeline_id,
            classification=result.classification,
            plan=result.plan,
            coding=result.coding,
            review=result.review,
            evaluation=result.evaluation,
            workspace_path=result.workspace_path,
            review_workspace_path=result.review_workspace_path,
            isolated=result.isolated,
            retry_count=result.retry_count,
            merge_ready=result.merge_ready,
            change_set=result.change_set,
            summary=summary,
            metadata={
                "coder_worktree": str(coder_worktree.path) if coder_worktree is not None else "",
                "reviewer_worktree": str(reviewer_worktree.path) if reviewer_worktree is not None else "",
            },
        )

    async def _invoke_coder(
        self,
        instruction: str,
        active_files: tuple[str, ...],
        context_manager: ContextManager,
        plan,
        task_tag: TaskTag,
        pipeline_id: str,
        *,
        coder_attempt: int,
        model_hint: str | None,
    ) -> str:
        request = self._coder.build_request(
            instruction=instruction,
            plan=plan,
            active_files=active_files,
            context_manager=context_manager,
            task_tag=task_tag,
            model_hint=model_hint or self._runtime_state.manual_model_alias,
        )
        try:
            routes = await self._broker.candidate_routes(request)
        except BrokerError:
            return ""

        for index, route in enumerate(routes):
            self._runtime_state.active_provider = route.provider_id
            self._runtime_state.active_model = route.alias or route.model_id
            turn_id = str(uuid4())
            await self._event_bus.publish(
                EventEnvelope.create(
                    kind=EventKind.PROVIDER_SELECTED,
                    session_id=self._session.session_id,
                    turn_id=turn_id,
                    task_tag=task_tag,
                    provider_id=route.provider_id,
                    model_id=route.model_id,
                    pipeline_id=pipeline_id,
                    payload={"agent_role": AgentRole.CODER.value, "route_attempt": index + 1, "coder_attempt": coder_attempt},
                )
            )
            adapter = self._adapter_factory.create(route)
            try:
                result = await adapter.chat(request)
            except Exception:
                continue
            self._session.request_count += 1
            self._session.total_cost_usd += result.cost_usd or 0.0
            self._session.last_model_alias = route.alias or route.model_id
            self._session.last_turn_id = turn_id
            await self._event_bus.publish(
                EventEnvelope.create(
                    kind=EventKind.MODEL_INVOKED,
                    session_id=self._session.session_id,
                    turn_id=turn_id,
                    task_tag=task_tag,
                    provider_id=route.provider_id,
                    model_id=route.model_id,
                    pipeline_id=pipeline_id,
                    payload={
                        "agent_role": AgentRole.CODER.value,
                        "input_tokens": result.input_tokens,
                        "output_tokens": result.output_tokens,
                        "latency_ms": result.latency_ms,
                        "cost_usd": result.cost_usd,
                        "response_excerpt": result.text[:500],
                        "coder_attempt": coder_attempt,
                    },
                )
            )
            return result.text
        return ""

    def _apply_edit_plan(self, plan, workspace_root: Path, run_id: str, isolated: bool) -> CoderOutput:
        artifact_dir = self._artifact_dir / "agent-runs" / run_id
        patch_service = PatchService(WorkspaceFiles(workspace_root, artifact_dir))
        git_workspace = GitWorkspace(workspace_root)
        applied_files: list[str] = []
        diff_blocks: list[str] = []
        backups: list[tuple[str, str | None]] = []
        for edit in plan.edits:
            try:
                patch = patch_service.replace_text(edit.path, edit.old, edit.new)
            except (FileNotFoundError, ValueError) as exc:
                for path, backup_path in reversed(backups):
                    patch_service.undo(path, backup_path)
                raise RuntimeError(f"Failed to apply edit for {edit.path}: {exc}") from exc
            applied_files.append(edit.path)
            backups.append((edit.path, patch.backup_path))
            label = f"{edit.path}: {edit.reason}" if edit.reason else edit.path
            diff_blocks.append(label + "\n" + patch.diff)
        diff_summary = git_workspace.diff_summary(tuple(applied_files))
        if not diff_summary.strip():
            diff_summary = "\n\n".join(diff_blocks)
        return CoderOutput(
            applied_files=tuple(applied_files),
            edit_count=len(plan.edits),
            diff_summary=diff_summary,
            workspace_path=str(workspace_root),
            isolated=isolated,
        )

    def _build_change_set(
        self,
        applied_files: tuple[str, ...],
        workspace_root: Path,
        run_id: str,
        *,
        isolated: bool,
    ) -> ChangeSet | None:
        if not isolated or not applied_files:
            return None
        builder = ChangeSetBuilder(
            self._project_root,
            workspace_root,
            self._artifact_dir / "agent-runs" / run_id / "merge",
        )
        return builder.build(applied_files)

    def _materialize_change_set(self, change_set: ChangeSet, workspace_root: Path, run_id: str, *, label: str) -> None:
        patch_service = PatchService(
            WorkspaceFiles(workspace_root, self._artifact_dir / "agent-runs" / run_id / f"{label}-materialized")
        )
        result = ChangeSetApplier(patch_service).apply(change_set)
        if result.conflicts:
            raise RuntimeError(f"Failed to materialize change set for {label}: {', '.join(result.conflicts)}")

    def _prepare_review_workspace(
        self,
        *,
        pipeline: PipelineDefinition,
        change_set: ChangeSet | None,
        coder_workspace: Path,
        active_files: tuple[str, ...],
        run_id: str,
        attempt: int,
    ) -> tuple[Path, WorktreeHandle | None]:
        review_workspace = coder_workspace
        reviewer_worktree: WorktreeHandle | None = None
        if AgentRole.REVIEWER not in pipeline.roles or change_set is None or change_set.is_empty():
            return review_workspace, reviewer_worktree
        if AgentRole.REVIEWER in pipeline.isolated_roles and self._worktrees.is_supported():
            reviewer_worktree = self._worktrees.create(f"{run_id}-reviewer-{attempt}")
            review_workspace = reviewer_worktree.path
            self._sync_active_files_to_workspace(active_files, review_workspace)
            self._materialize_change_set(change_set, review_workspace, run_id, label=f"reviewer-{attempt}")
        return review_workspace, reviewer_worktree

    def _retry_instruction(self, instruction: str, failure_summary: str, attempt: int) -> str:
        if attempt <= 1 or not failure_summary.strip():
            return instruction
        return (
            f"{instruction}\n\n"
            "Previous verification failed. Update the plan to address the failure summary below.\n"
            f"{failure_summary}"
        )

    async def _default_benchmark_aliases(self) -> tuple[str, ...]:
        snapshot = await self._health_service.refresh()
        aliases: list[str] = []
        if self._provider_registry is None:
            return (self._runtime_state.manual_model_alias,) if self._runtime_state.manual_model_alias else ("mock",)
        for route in self._provider_registry.ordered_routes():
            key = self._health_service.route_key(route)
            status = snapshot.get(key)
            if status is None or status.state.value not in {"healthy", "degraded"}:
                continue
            aliases.append(route.alias or route.model_id)
        if aliases:
            return tuple(aliases)
        if self._runtime_state.manual_model_alias:
            return (self._runtime_state.manual_model_alias,)
        return ("mock",)

    def _sync_active_files_to_workspace(self, active_files: tuple[str, ...], workspace_root: Path) -> None:
        source = WorkspaceFiles(self._project_root, self._artifact_dir / "source-sync")
        target = WorkspaceFiles(workspace_root, self._artifact_dir / "worktree-sync")
        for path in active_files:
            content = source.read_text(path)
            if content is None:
                continue
            target.write_text(path, content)

    def _tool_executor(self):
        from ..execution.shell import ShellToolExecutor

        return ShellToolExecutor()


def isolation_enabled(isolated: bool, worktree: WorktreeHandle | None) -> bool:
    return isolated and worktree is not None
