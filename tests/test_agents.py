from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codecore.agents import MultiAgentRunner, TaskClassifier
from codecore.agents.models import EvaluationOutput
from codecore.context.composer import DefaultContextComposer
from codecore.context.manager import ContextManager
from codecore.domain.enums import HealthState, TaskTag
from codecore.domain.models import ChatResult, HealthStatus
from codecore.execution.approvals import ApprovalManager
from codecore.execution.audit import FileChangeAudit
from codecore.execution.files import WorkspaceFiles
from codecore.execution.patches import PatchService
from codecore.execution.worktrees import WorktreeManager
from codecore.infra.manifest_loader import load_provider_registry
from codecore.infra.project_manifest import ProjectManifest
from codecore.kernel.event_bus import EventBus
from codecore.kernel.orchestrator import Orchestrator
from codecore.kernel.runtime_state import RuntimeState
from codecore.kernel.session import new_session_runtime
from codecore.providers.adapters.base import AdapterFactory
from codecore.providers.broker import PolicyDrivenBroker
from codecore.providers.health import ProviderHealthService
from codecore.providers.manifests import ProviderManifest, ProviderModelManifest, ProviderRegistryManifest
from codecore.providers.registry import ProviderRegistry


class AgentRuntimeTest(unittest.TestCase):
    def test_classifier_picks_complex_pipeline_for_multi_file_scope(self) -> None:
        result = TaskClassifier().classify(
            "refactor the pipeline and review the changes",
            task_tag=TaskTag.CODE,
            active_files=("a.py", "b.py", "c.py"),
        )
        self.assertEqual(result.pipeline_id, "planner-coder-reviewer")
        self.assertEqual(result.complexity, "complex")

    def test_worktree_manager_creates_and_removes_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            init_git_repo(temp_path)
            manager = WorktreeManager(temp_path, temp_path / ".artifacts" / "worktrees")

            handle = manager.create("coder-ctx")
            listed = manager.list()

            self.assertTrue(handle.path.exists())
            self.assertIn(handle.path, tuple(item.path for item in listed))
            manager.remove(handle)
            self.assertFalse(handle.path.exists())

    def test_delegate_runs_pipeline_in_isolated_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            init_git_repo(temp_path)
            (temp_path / "notes.txt").write_text("before\n", encoding="utf-8")
            subprocess.run(["git", "add", "notes.txt"], cwd=temp_path, check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", "add notes"], cwd=temp_path, check=True, capture_output=True, text=True)
            orchestrator = build_orchestrator(temp_path)

            async def run() -> str:
                await orchestrator.handle_line("/add notes.txt")
                result = await orchestrator.handle_line('/delegate "change before to after"')
                self.assertFalse(result.is_error)
                return result.output or ""

            output = asyncio.run(run())
            workspace = next(line.split("=", 1)[1] for line in output.splitlines() if line.startswith("workspace="))
            self.assertIn("pipeline=coder-only", output)
            self.assertIn("isolation=enabled", output)
            self.assertEqual((temp_path / "notes.txt").read_text(encoding="utf-8"), "before\n")
            self.assertEqual((Path(workspace) / "notes.txt").read_text(encoding="utf-8"), "after\n")

    def test_delegate_uses_separate_reviewer_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            init_git_repo(temp_path)
            (temp_path / "notes.txt").write_text("before\n", encoding="utf-8")
            (temp_path / "a.txt").write_text("alpha\n", encoding="utf-8")
            (temp_path / "b.txt").write_text("beta\n", encoding="utf-8")
            subprocess.run(["git", "add", "notes.txt", "a.txt", "b.txt"], cwd=temp_path, check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", "add fixtures"], cwd=temp_path, check=True, capture_output=True, text=True)
            orchestrator = build_orchestrator(temp_path)

            async def run() -> str:
                await orchestrator.handle_line("/add notes.txt a.txt b.txt")
                result = await orchestrator.handle_line('/delegate "review and change before to after"')
                self.assertFalse(result.is_error)
                return result.output or ""

            output = asyncio.run(run())
            coder_workspace = next(line.split("=", 1)[1] for line in output.splitlines() if line.startswith("workspace="))
            review_workspace = next(
                line.split("=", 1)[1] for line in output.splitlines() if line.startswith("review_workspace=")
            )
            self.assertIn("pipeline=planner-coder-reviewer", output)
            self.assertNotEqual(coder_workspace, review_workspace)
            self.assertEqual((temp_path / "notes.txt").read_text(encoding="utf-8"), "before\n")
            self.assertEqual((Path(coder_workspace) / "notes.txt").read_text(encoding="utf-8"), "after\n")
            self.assertEqual((Path(review_workspace) / "notes.txt").read_text(encoding="utf-8"), "after\n")

    def test_delegate_apply_requires_approval_and_updates_main_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            init_git_repo(temp_path)
            (temp_path / "notes.txt").write_text("before\n", encoding="utf-8")
            subprocess.run(["git", "add", "notes.txt"], cwd=temp_path, check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", "add notes"], cwd=temp_path, check=True, capture_output=True, text=True)
            orchestrator = build_orchestrator(temp_path, with_approvals=True)

            async def run() -> tuple[str, str]:
                await orchestrator.handle_line("/add notes.txt")
                delegated = await orchestrator.handle_line('/delegate --apply "change before to after"')
                self.assertTrue(delegated.is_error)
                approved = await orchestrator.handle_line("/approve latest")
                self.assertFalse(approved.is_error)
                return delegated.output or "", approved.output or ""

            delegated_output, approved_output = asyncio.run(run())
            self.assertIn("Approval required:", delegated_output)
            self.assertIn("applied_change_set=1", approved_output)
            self.assertEqual((temp_path / "notes.txt").read_text(encoding="utf-8"), "after\n")

    def test_delegate_apply_detects_conflicts_before_merge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            init_git_repo(temp_path)
            (temp_path / "notes.txt").write_text("before\n", encoding="utf-8")
            subprocess.run(["git", "add", "notes.txt"], cwd=temp_path, check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", "add notes"], cwd=temp_path, check=True, capture_output=True, text=True)
            orchestrator = build_orchestrator(temp_path, with_approvals=True)

            async def run() -> str:
                await orchestrator.handle_line("/add notes.txt")
                delegated = await orchestrator.handle_line('/delegate --apply "change before to after"')
                self.assertTrue(delegated.is_error)
                (temp_path / "notes.txt").write_text("manual\n", encoding="utf-8")
                approved = await orchestrator.handle_line("/approve latest")
                self.assertTrue(approved.is_error)
                return approved.output or ""

            approved_output = asyncio.run(run())
            self.assertIn("conflicts", approved_output.lower())
            self.assertEqual((temp_path / "notes.txt").read_text(encoding="utf-8"), "manual\n")

    def test_multi_agent_runner_retries_failed_evaluation_before_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            init_git_repo(temp_path)
            (temp_path / "notes.txt").write_text("before\n", encoding="utf-8")
            (temp_path / "a.txt").write_text("alpha\n", encoding="utf-8")
            (temp_path / "b.txt").write_text("beta\n", encoding="utf-8")
            subprocess.run(["git", "add", "notes.txt", "a.txt", "b.txt"], cwd=temp_path, check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", "add retry fixtures"], cwd=temp_path, check=True, capture_output=True, text=True)
            registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
            health = ProviderHealthService(registry, AdapterFactory())
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            runner = MultiAgentRunner(
                project_root=temp_path,
                artifact_dir=temp_path / ".artifacts",
                session=session,
                runtime_state=runtime_state,
                broker=PolicyDrivenBroker(registry, health),
                health_service=health,
                adapter_factory=SequenceAdapterFactory(
                    [
                        ChatResult(
                            text='{"edits":[{"path":"notes.txt","old":"before","new":"broken","reason":"introduce failing state"}]}'
                        ),
                        ChatResult(
                            text='{"edits":[{"path":"notes.txt","old":"broken","new":"after","reason":"fix failing state"}]}'
                        ),
                    ]
                ),
                event_bus=EventBus(sinks=[]),
                worktree_manager=WorktreeManager(temp_path, temp_path / ".artifacts" / "worktrees"),
                evaluator=FileContentEvaluator(),
            )

            result = asyncio.run(
                runner.run(
                    instruction="review and change before to after",
                    active_files=("notes.txt", "a.txt", "b.txt"),
                    task_tag=TaskTag.CODE,
                )
            )

            self.assertEqual(result.pipeline_id, "planner-coder-reviewer")
            self.assertEqual(result.retry_count, 1)
            self.assertIsNotNone(result.review)
            self.assertTrue(result.review.approved)
            self.assertIsNotNone(result.evaluation)
            self.assertEqual(result.evaluation.status, "passed")
            self.assertIn("retries=1", result.summary)
            self.assertEqual((temp_path / "notes.txt").read_text(encoding="utf-8"), "before\n")
            self.assertEqual((Path(result.workspace_path or "") / "notes.txt").read_text(encoding="utf-8"), "after\n")

    def test_orchestrator_benchmark_compares_multiple_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            init_git_repo(temp_path)
            (temp_path / "notes.txt").write_text("before\n", encoding="utf-8")
            subprocess.run(["git", "add", "notes.txt"], cwd=temp_path, check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", "add notes"], cwd=temp_path, check=True, capture_output=True, text=True)
            orchestrator = build_benchmark_orchestrator(temp_path)

            async def run() -> str:
                await orchestrator.handle_line("/add notes.txt")
                result = await orchestrator.handle_line('/benchmark --models alpha,beta "change before to after"')
                self.assertFalse(result.is_error)
                return result.output or ""

            output = asyncio.run(run())
            self.assertIn("benchmark_models=2", output)
            self.assertIn("alpha | pipeline=coder-only | status=ok", output)
            self.assertIn("beta | pipeline=coder-only | status=ok", output)
            self.assertEqual((temp_path / "notes.txt").read_text(encoding="utf-8"), "before\n")


def build_orchestrator(temp_path: Path, *, with_approvals: bool = False) -> Orchestrator:
    registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
    adapter_factory = AdapterFactory()
    health = ProviderHealthService(registry, adapter_factory)
    session = new_session_runtime()
    runtime_state = RuntimeState.default()
    context_manager = ContextManager(temp_path)
    event_bus = EventBus(sinks=[])
    runner = MultiAgentRunner(
        project_root=temp_path,
        artifact_dir=temp_path / ".artifacts",
        session=session,
        runtime_state=runtime_state,
        broker=PolicyDrivenBroker(registry, health),
        health_service=health,
        adapter_factory=adapter_factory,
        event_bus=event_bus,
        worktree_manager=WorktreeManager(temp_path, temp_path / ".artifacts" / "worktrees"),
    )
    patch_service = PatchService(WorkspaceFiles(temp_path, temp_path / ".artifacts" / "main-workspace"))
    approval_manager = ApprovalManager() if with_approvals else None
    file_change_audit = FileChangeAudit(temp_path / ".artifacts" / "file-changes.jsonl") if with_approvals else None
    return Orchestrator(
        session=session,
        runtime_state=runtime_state,
        provider_registry=registry,
        broker=PolicyDrivenBroker(registry, health),
        health_service=health,
        adapter_factory=adapter_factory,
        context_manager=context_manager,
        context_composer=DefaultContextComposer(
            context_manager,
            session,
            runtime_state,
            ProjectManifest(project_id="temp-agent"),
        ),
        event_bus=event_bus,
        multi_agent_runner=runner,
        patch_service=patch_service,
        approval_manager=approval_manager,
        file_change_audit=file_change_audit,
    )


def build_benchmark_orchestrator(temp_path: Path) -> Orchestrator:
    registry = ProviderRegistry(
        ProviderRegistryManifest(
            providers=[
                ProviderManifest(
                    provider_id="bench-alpha",
                    transport="internal",
                    priority=1,
                    models=[ProviderModelManifest(id="alpha-model", alias="alpha", supports_json=True)],
                ),
                ProviderManifest(
                    provider_id="bench-beta",
                    transport="internal",
                    priority=2,
                    models=[ProviderModelManifest(id="beta-model", alias="beta", supports_json=True)],
                ),
            ]
        )
    )
    adapter_factory = AliasAwareAdapterFactory(
        {
            "alpha": ChatResult(
                text='{"edits":[{"path":"notes.txt","old":"before","new":"after-alpha","reason":"alpha replacement"}]}'
            ),
            "beta": ChatResult(
                text='{"edits":[{"path":"notes.txt","old":"before","new":"after-beta","reason":"beta replacement"}]}'
            ),
        }
    )
    health = ProviderHealthService(registry, adapter_factory)
    session = new_session_runtime()
    runtime_state = RuntimeState.default()
    context_manager = ContextManager(temp_path)
    event_bus = EventBus(sinks=[])
    runner = MultiAgentRunner(
        project_root=temp_path,
        artifact_dir=temp_path / ".artifacts",
        session=session,
        runtime_state=runtime_state,
        broker=PolicyDrivenBroker(registry, health),
        health_service=health,
        adapter_factory=adapter_factory,
        event_bus=event_bus,
        worktree_manager=WorktreeManager(temp_path, temp_path / ".artifacts" / "worktrees"),
        evaluator=PassingEvaluator(),
    )
    return Orchestrator(
        session=session,
        runtime_state=runtime_state,
        provider_registry=registry,
        broker=PolicyDrivenBroker(registry, health),
        health_service=health,
        adapter_factory=adapter_factory,
        context_manager=context_manager,
        context_composer=DefaultContextComposer(
            context_manager,
            session,
            runtime_state,
            ProjectManifest(project_id="temp-benchmark"),
        ),
        event_bus=event_bus,
        multi_agent_runner=runner,
    )


class SequenceAdapterFactory:
    def __init__(self, responses: list[ChatResult]) -> None:
        self._responses = responses

    def create(self, _route):
        return SequenceAdapter(self._responses)


class SequenceAdapter:
    def __init__(self, responses: list[ChatResult]) -> None:
        self._responses = responses

    async def chat(self, _request) -> ChatResult:
        if not self._responses:
            raise RuntimeError("No more queued responses.")
        return self._responses.pop(0)


class FileContentEvaluator:
    async def evaluate(self, project_root: Path) -> EvaluationOutput:
        content = (project_root / "notes.txt").read_text(encoding="utf-8")
        if "broken" in content:
            return EvaluationOutput(
                status="failed",
                summary="content-check failed: broken marker still present",
                checks_run=("content-check",),
            )
        return EvaluationOutput(
            status="passed",
            summary="content-check passed",
            checks_run=("content-check",),
        )


class AliasAwareAdapterFactory:
    def __init__(self, responses: dict[str, ChatResult]) -> None:
        self._responses = responses

    def create(self, route):
        alias = route.alias or route.model_id
        response = self._responses[alias]
        return StaticAdapter(response)


class StaticAdapter:
    def __init__(self, response: ChatResult) -> None:
        self._response = response

    async def chat(self, _request) -> ChatResult:
        return self._response

    async def health(self) -> HealthStatus:
        return HealthStatus(state=HealthState.HEALTHY, checked_at=HealthStatus.unknown().checked_at, detail="ready")


class PassingEvaluator:
    async def evaluate(self, _project_root: Path) -> EvaluationOutput:
        return EvaluationOutput(status="passed", summary="benchmark passed", checks_run=("benchmark-check",))


def init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "CodeCore Test"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    (path / "README.md").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
