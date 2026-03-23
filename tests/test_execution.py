from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codecore.context.composer import DefaultContextComposer
from codecore.context.manager import ContextManager
from codecore.domain.enums import EventKind, PolicyAction, RiskLevel, TaskTag
from codecore.domain.events import EventEnvelope
from codecore.domain.models import ChatMessage, ChatRequest, ChatResult
from codecore.execution.audit import FileChangeAudit
from codecore.execution.approvals import ApprovalManager
from codecore.execution.files import WorkspaceFiles
from codecore.execution.git import GitWorkspace
from codecore.execution.native_tools import NativeRepositoryTools
from codecore.execution.patches import PatchService
from codecore.execution.sandbox import SandboxProfile
from codecore.execution.shell import ShellToolExecutor, summarize_output
from codecore.execution.tests import VerificationRunner
from codecore.governance.policy import SimplePolicyEngine
from codecore.infra.manifest_loader import load_project_manifest, load_provider_registry
from codecore.infra.project_manifest import ProjectManifest
from codecore.kernel.event_bus import EventBus
from codecore.kernel.orchestrator import Orchestrator
from codecore.kernel.runtime_state import RuntimeState
from codecore.kernel.session import new_session_runtime
from codecore.providers.adapters.base import AdapterFactory
from codecore.providers.broker import PolicyDrivenBroker
from codecore.providers.health import ProviderHealthService
from codecore.providers.registry import ProviderRegistry
from codecore.providers.capabilities import route_capabilities


class RecordingSink:
    def __init__(self) -> None:
        self.events: list[EventEnvelope] = []

    async def publish(self, event: EventEnvelope) -> None:
        self.events.append(event)


class ScriptedAdapter:
    def __init__(self, route, response_text: str) -> None:
        self._route = route
        self._response_text = response_text

    async def chat(self, request):
        return ChatResult(text=self._response_text, latency_ms=5, metadata={"scripted": True})

    async def stream(self, request):
        yield self._response_text

    async def health(self):
        from codecore.domain.enums import HealthState
        from codecore.domain.models import HealthStatus

        return HealthStatus(state=HealthState.HEALTHY, checked_at=HealthStatus.unknown().checked_at, detail="ok")

    def capabilities(self):
        return route_capabilities(self._route)


class ScriptedAdapterFactory:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text

    def create(self, route):
        return ScriptedAdapter(route, self._response_text)


class ScriptedSequenceAdapterFactory:
    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def create(self, route):
        return _ScriptedSequenceAdapter(route, self)


class _ScriptedSequenceAdapter:
    def __init__(self, route, factory: ScriptedSequenceAdapterFactory) -> None:
        self._route = route
        self._factory = factory

    async def chat(self, request):
        response = self._factory._responses[min(self._factory.calls, len(self._factory._responses) - 1)]
        self._factory.calls += 1
        return ChatResult(text=response, latency_ms=5, metadata={"scripted": True})

    async def stream(self, request):
        response = self._factory._responses[min(self._factory.calls, len(self._factory._responses) - 1)]
        self._factory.calls += 1
        yield response

    async def health(self):
        from codecore.domain.enums import HealthState
        from codecore.domain.models import HealthStatus

        return HealthStatus(state=HealthState.HEALTHY, checked_at=HealthStatus.unknown().checked_at, detail="ok")

    def capabilities(self):
        return route_capabilities(self._route)


class ExecutionRuntimeTest(unittest.TestCase):
    def test_policy_allows_read_only_command(self) -> None:
        decision = SimplePolicyEngine().evaluate_command("pwd")
        self.assertEqual(decision.action, PolicyAction.ALLOW)
        self.assertEqual(decision.risk_level, RiskLevel.READ_ONLY)

    def test_policy_blocks_mutating_command(self) -> None:
        decision = SimplePolicyEngine().evaluate_command("rm -rf tmp")
        self.assertEqual(decision.action, PolicyAction.REQUIRE_APPROVAL)
        self.assertEqual(decision.risk_level, RiskLevel.WORKSPACE_WRITE)

    def test_shell_executor_summarizes_large_output(self) -> None:
        summary = summarize_output("\n".join(f"line {index}" for index in range(60)), max_chars=120)
        self.assertTrue(summary.truncated)
        self.assertIn("omitted", summary.rendered)

    def test_sandbox_profile_for_risk(self) -> None:
        profile = SandboxProfile.for_risk(RiskLevel.WORKSPACE_WRITE, approved=True)
        self.assertTrue(profile.allow_workspace_write)
        self.assertEqual(profile.name, "workspace-write")

    def test_orchestrator_runs_read_only_command(self) -> None:
        registry = ProviderRegistry(load_provider_registry(ROOT / ".codecore" / "providers" / "registry.yaml"))
        health = ProviderHealthService(registry, AdapterFactory())
        sink = RecordingSink()
        session = new_session_runtime()
        session.task_tag = TaskTag.RUN
        runtime_state = RuntimeState.default()
        context_manager = ContextManager(ROOT)
        orchestrator = Orchestrator(
            session=session,
            runtime_state=runtime_state,
            provider_registry=registry,
            broker=PolicyDrivenBroker(registry, health),
            health_service=health,
            adapter_factory=AdapterFactory(),
            context_manager=context_manager,
            context_composer=DefaultContextComposer(
                context_manager,
                session,
                runtime_state,
                load_project_manifest(ROOT / ".codecore" / "project.yaml"),
            ),
            event_bus=EventBus(sinks=[sink]),
            tool_executor=ShellToolExecutor(),
            policy_engine=SimplePolicyEngine(),
        )

        async def run() -> str:
            result = await orchestrator.handle_line("/run pwd")
            self.assertFalse(result.is_error)
            return result.output or ""

        output = asyncio.run(run())
        self.assertIn("exit_code=0", output)
        self.assertIn(str(ROOT), output)
        kinds = [event.kind for event in sink.events]
        self.assertIn(EventKind.TOOL_CALLED, kinds)
        self.assertIn(EventKind.TOOL_FINISHED, kinds)

    def test_orchestrator_blocks_mutating_run_command(self) -> None:
        registry = ProviderRegistry(load_provider_registry(ROOT / ".codecore" / "providers" / "registry.yaml"))
        health = ProviderHealthService(registry, AdapterFactory())
        sink = RecordingSink()
        session = new_session_runtime()
        runtime_state = RuntimeState.default()
        context_manager = ContextManager(ROOT)
        orchestrator = Orchestrator(
            session=session,
            runtime_state=runtime_state,
            provider_registry=registry,
            broker=PolicyDrivenBroker(registry, health),
            health_service=health,
            adapter_factory=AdapterFactory(),
            context_manager=context_manager,
            context_composer=DefaultContextComposer(
                context_manager,
                session,
                runtime_state,
                load_project_manifest(ROOT / ".codecore" / "project.yaml"),
            ),
            event_bus=EventBus(sinks=[sink]),
            tool_executor=ShellToolExecutor(),
            policy_engine=SimplePolicyEngine(),
        )

        async def run() -> str:
            result = await orchestrator.handle_line("/run rm -rf tmp")
            self.assertTrue(result.is_error)
            return result.output or ""

        output = asyncio.run(run())
        self.assertIn("Safer alternative:", output)
        kinds = [event.kind for event in sink.events]
        self.assertIn(EventKind.POLICY_BLOCKED, kinds)

    def test_orchestrator_approval_flow_executes_command(self) -> None:
        registry = ProviderRegistry(load_provider_registry(ROOT / ".codecore" / "providers" / "registry.yaml"))
        health = ProviderHealthService(registry, AdapterFactory())
        sink = RecordingSink()
        session = new_session_runtime()
        runtime_state = RuntimeState.default()
        context_manager = ContextManager(ROOT)
        approvals = ApprovalManager()
        orchestrator = Orchestrator(
            session=session,
            runtime_state=runtime_state,
            provider_registry=registry,
            broker=PolicyDrivenBroker(registry, health),
            health_service=health,
            adapter_factory=AdapterFactory(),
            context_manager=context_manager,
            context_composer=DefaultContextComposer(
                context_manager,
                session,
                runtime_state,
                load_project_manifest(ROOT / ".codecore" / "project.yaml"),
            ),
            event_bus=EventBus(sinks=[sink]),
            tool_executor=ShellToolExecutor(),
            policy_engine=SimplePolicyEngine(),
            approval_manager=approvals,
        )

        async def run() -> tuple[str, str]:
            blocked = await orchestrator.handle_line("/run echo hello")
            approval_id = blocked.output.split("Approval required: ", 1)[1].splitlines()[0]
            approved = await orchestrator.handle_line(f"/approve {approval_id}")
            return blocked.output or "", approved.output or ""

        blocked_output, approved_output = asyncio.run(run())
        self.assertIn("Approval required:", blocked_output)
        self.assertIn("stdout:\nhello", approved_output)
        self.assertIn("sandbox=workspace-write", approved_output)

    def test_prompt_tool_loop_reads_file_and_answers_in_one_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            docs_dir = temp_path / "docs"
            docs_dir.mkdir()
            (docs_dir / "SPEC.md").write_text("# Spec\nCurrent bot flow handles psychotype results.\n", encoding="utf-8")
            registry = ProviderRegistry(load_provider_registry(ROOT / ".codecore" / "providers" / "registry.yaml"))
            adapter_factory = ScriptedSequenceAdapterFactory(
                [
                    json.dumps(
                        {
                            "action": "tool",
                            "tool": "read",
                            "args": {"path": "docs/SPEC.md", "start_line": 1, "end_line": 20},
                            "message": "Reading the main specification.",
                        }
                    ),
                    json.dumps(
                        {
                            "action": "answer",
                            "answer": "Кратко: текущий сценарий завязан на обработке результата психотипа.",
                        }
                    ),
                ]
            )
            health = ProviderHealthService(registry, adapter_factory)
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            context_manager = ContextManager(temp_path)
            orchestrator = Orchestrator(
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
                    ProjectManifest(project_id="temp-tool-loop"),
                ),
                event_bus=EventBus(sinks=[]),
                native_tool_executor=NativeRepositoryTools(context_manager),
            )

            async def run() -> str:
                result = await orchestrator.handle_line("Напиши кратко что в docs/SPEC.md про психотип")
                self.assertFalse(result.is_error)
                return result.output or ""

            output = asyncio.run(run())
            self.assertIn("текущий сценарий", output.lower())
            self.assertIn("docs/SPEC.md", session.active_files)
            self.assertEqual(adapter_factory.calls, 2)

    def test_prompt_tool_loop_searches_then_answers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            bot_dir = temp_path / "bot"
            bot_dir.mkdir()
            (bot_dir / "states.py").write_text("PSYCHOTYPE_READY = 'ready'\n", encoding="utf-8")
            registry = ProviderRegistry(load_provider_registry(ROOT / ".codecore" / "providers" / "registry.yaml"))
            adapter_factory = ScriptedSequenceAdapterFactory(
                [
                    json.dumps(
                        {
                            "action": "tool",
                            "tool": "search",
                            "args": {"query": "PSYCHOTYPE_READY", "path": "bot", "max_matches": 5},
                            "message": "Searching bot states for psychotype handling.",
                        }
                    ),
                    json.dumps(
                        {
                            "action": "answer",
                            "answer": "Нашел точку входа: состояние `PSYCHOTYPE_READY` определено в `bot/states.py`.",
                        }
                    ),
                ]
            )
            health = ProviderHealthService(registry, adapter_factory)
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            context_manager = ContextManager(temp_path)
            orchestrator = Orchestrator(
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
                    ProjectManifest(project_id="temp-tool-loop-search"),
                ),
                event_bus=EventBus(sinks=[]),
                native_tool_executor=NativeRepositoryTools(context_manager),
            )

            async def run() -> str:
                result = await orchestrator.handle_line("Где у нас определяется состояние психотипа?")
                self.assertFalse(result.is_error)
                return result.output or ""

            output = asyncio.run(run())
            self.assertIn("bot/states.py", output)
            self.assertEqual(adapter_factory.calls, 2)

    def test_verify_command_runs_explicit_unittest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tests_dir = temp_path / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_sample.py").write_text(
                "import unittest\n\nclass Smoke(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
            health = ProviderHealthService(registry, AdapterFactory())
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            context_manager = ContextManager(temp_path)
            orchestrator = Orchestrator(
                session=session,
                runtime_state=runtime_state,
                provider_registry=registry,
                broker=PolicyDrivenBroker(registry, health),
                health_service=health,
                adapter_factory=AdapterFactory(),
                context_manager=context_manager,
                context_composer=DefaultContextComposer(
                    context_manager,
                    session,
                    runtime_state,
                    ProjectManifest(project_id="temp-verify"),
                ),
                event_bus=EventBus(sinks=[]),
                tool_executor=ShellToolExecutor(),
                policy_engine=SimplePolicyEngine(),
                verification_engine=VerificationRunner(ShellToolExecutor(), temp_path),
            )

            async def run() -> str:
                result = await orchestrator.handle_line("/verify python3 -m unittest discover -s tests -v")
                self.assertFalse(result.is_error)
                return result.output or ""

            output = asyncio.run(run())
            self.assertIn("passed=True", output)
            self.assertIn("test_ok", output)

    def test_tool_outputs_are_injected_into_prompt(self) -> None:
        registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
        health = ProviderHealthService(registry, AdapterFactory())
        session = new_session_runtime()
        session.task_tag = TaskTag.RUN
        runtime_state = RuntimeState.default()
        context_manager = ContextManager(ROOT)
        composer = DefaultContextComposer(
            context_manager,
            session,
            runtime_state,
            load_project_manifest(ROOT / ".codecore" / "project.yaml"),
        )
        orchestrator = Orchestrator(
            session=session,
            runtime_state=runtime_state,
            provider_registry=registry,
            broker=PolicyDrivenBroker(registry, health),
            health_service=health,
            adapter_factory=AdapterFactory(),
            context_manager=context_manager,
            context_composer=composer,
            event_bus=EventBus(sinks=[]),
            tool_executor=ShellToolExecutor(),
            policy_engine=SimplePolicyEngine(),
        )

        async def run() -> str:
            await orchestrator.handle_line("/run pwd")
            request = await composer.compose(
                ChatRequest(messages=(ChatMessage(role="user", content="why did the command fail"),), task_tag=TaskTag.RUN)
            )
            return request.system_prompt

        prompt = asyncio.run(run())
        self.assertIn("Recent tool outputs:", prompt)
        self.assertIn("shell: pwd", prompt)

    def test_git_workspace_diff_and_restore(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            init_git_repo(temp_path)
            readme = temp_path / "README.md"
            readme.write_text("changed\n", encoding="utf-8")
            workspace = GitWorkspace(temp_path)

            diff_text = workspace.diff_summary(("README.md",))
            restore_text = workspace.restore(("README.md",))

            self.assertIn("status:", diff_text)
            self.assertIn("diff:", diff_text)
            self.assertIn("Restored tracked files: README.md", restore_text)
            self.assertEqual(readme.read_text(encoding="utf-8"), "initial\n")

    def test_workspace_files_and_patch_service(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files = WorkspaceFiles(temp_path, temp_path / ".artifacts")
            patch_service = PatchService(files)
            target = temp_path / "notes.txt"
            target.write_text("before\n", encoding="utf-8")

            application = patch_service.replace_file("notes.txt", "after\n")

            self.assertIn("--- a/notes.txt", application.diff)
            self.assertTrue(target.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "after\n")
            patch_service.undo("notes.txt", application.backup_path)
            self.assertEqual(target.read_text(encoding="utf-8"), "before\n")

    def test_patch_service_replace_text_requires_unique_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            files = WorkspaceFiles(temp_path, temp_path / ".artifacts")
            patch_service = PatchService(files)
            target = temp_path / "notes.txt"
            target.write_text("alpha\nbeta\n", encoding="utf-8")

            application = patch_service.replace_text("notes.txt", "beta", "gamma")

            self.assertIn("+gamma", application.diff)
            self.assertEqual(target.read_text(encoding="utf-8"), "alpha\ngamma\n")

    def test_orchestrator_replace_requires_approval_and_audits_patch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "notes.txt").write_text("before\n", encoding="utf-8")
            registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
            health = ProviderHealthService(registry, AdapterFactory())
            sink = RecordingSink()
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            context_manager = ContextManager(temp_path)
            approvals = ApprovalManager()
            audit_path = temp_path / ".artifacts" / "file-changes.jsonl"
            orchestrator = Orchestrator(
                session=session,
                runtime_state=runtime_state,
                provider_registry=registry,
                broker=PolicyDrivenBroker(registry, health),
                health_service=health,
                adapter_factory=AdapterFactory(),
                context_manager=context_manager,
                context_composer=DefaultContextComposer(
                    context_manager,
                    session,
                    runtime_state,
                    ProjectManifest(project_id="temp-patch"),
                ),
                event_bus=EventBus(sinks=[sink]),
                patch_service=PatchService(WorkspaceFiles(temp_path, temp_path / ".artifacts")),
                approval_manager=approvals,
                file_change_audit=FileChangeAudit(audit_path),
            )

            async def run() -> tuple[str, str]:
                blocked = await orchestrator.handle_line('/replace notes.txt "before" "after"')
                approval_id = blocked.output.split("Approval required: ", 1)[1].splitlines()[0]
                approved = await orchestrator.handle_line(f"/approve {approval_id}")
                return blocked.output or "", approved.output or ""

            blocked_output, approved_output = asyncio.run(run())
            self.assertIn("Approval required:", blocked_output)
            self.assertIn("path=notes.txt", approved_output)
            self.assertIn("+after", approved_output)
            self.assertEqual((temp_path / "notes.txt").read_text(encoding="utf-8"), "after\n")
            self.assertIn("notes.txt", session.active_files)
            audit_records = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(audit_records[-1]["action"], "patch_applied")
            self.assertEqual(audit_records[-1]["path"], "notes.txt")
            self.assertIn(EventKind.PATCH_APPLIED, [event.kind for event in sink.events])

    def test_approvals_command_lists_pending_requests(self) -> None:
        registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
        health = ProviderHealthService(registry, AdapterFactory())
        session = new_session_runtime()
        runtime_state = RuntimeState.default()
        context_manager = ContextManager(ROOT)
        approvals = ApprovalManager()
        orchestrator = Orchestrator(
            session=session,
            runtime_state=runtime_state,
            provider_registry=registry,
            broker=PolicyDrivenBroker(registry, health),
            health_service=health,
            adapter_factory=AdapterFactory(),
            context_manager=context_manager,
            context_composer=DefaultContextComposer(
                context_manager,
                session,
                runtime_state,
                load_project_manifest(ROOT / ".codecore" / "project.yaml"),
            ),
            event_bus=EventBus(sinks=[]),
            tool_executor=ShellToolExecutor(),
            policy_engine=SimplePolicyEngine(),
            approval_manager=approvals,
        )

        async def run() -> str:
            await orchestrator.handle_line("/run echo hello")
            listing = await orchestrator.handle_line("/approvals")
            return listing.output or ""

        output = asyncio.run(run())
        self.assertIn("run | workspace_write | echo hello", output)

    def test_approve_latest_executes_most_recent_request(self) -> None:
        registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
        health = ProviderHealthService(registry, AdapterFactory())
        session = new_session_runtime()
        runtime_state = RuntimeState.default()
        context_manager = ContextManager(ROOT)
        approvals = ApprovalManager()
        orchestrator = Orchestrator(
            session=session,
            runtime_state=runtime_state,
            provider_registry=registry,
            broker=PolicyDrivenBroker(registry, health),
            health_service=health,
            adapter_factory=AdapterFactory(),
            context_manager=context_manager,
            context_composer=DefaultContextComposer(
                context_manager,
                session,
                runtime_state,
                load_project_manifest(ROOT / ".codecore" / "project.yaml"),
            ),
            event_bus=EventBus(sinks=[]),
            tool_executor=ShellToolExecutor(),
            policy_engine=SimplePolicyEngine(),
            approval_manager=approvals,
        )

        async def run() -> str:
            await orchestrator.handle_line("/run echo first")
            await orchestrator.handle_line("/run echo second")
            approved = await orchestrator.handle_line("/approve latest")
            return approved.output or ""

        output = asyncio.run(run())
        self.assertIn("stdout:\nsecond", output)

    def test_retry_replays_failed_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tests_dir = temp_path / "tests"
            tests_dir.mkdir()
            test_file = tests_dir / "test_sample.py"
            test_file.write_text(
                "import unittest\n\nclass Smoke(unittest.TestCase):\n    def test_fail(self):\n        self.assertTrue(False)\n",
                encoding="utf-8",
            )
            registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
            health = ProviderHealthService(registry, AdapterFactory())
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            context_manager = ContextManager(temp_path)
            orchestrator = Orchestrator(
                session=session,
                runtime_state=runtime_state,
                provider_registry=registry,
                broker=PolicyDrivenBroker(registry, health),
                health_service=health,
                adapter_factory=AdapterFactory(),
                context_manager=context_manager,
                context_composer=DefaultContextComposer(
                    context_manager,
                    session,
                    runtime_state,
                    ProjectManifest(project_id="temp-retry"),
                ),
                event_bus=EventBus(sinks=[]),
                verification_engine=VerificationRunner(ShellToolExecutor(), temp_path),
            )

            async def run() -> tuple[str, str]:
                failed = await orchestrator.handle_line("/verify python3 -m unittest discover -s tests -v")
                test_file.write_text(
                    "import unittest\n\nclass Smoke(unittest.TestCase):\n    def test_fail(self):\n        self.assertTrue(True)\n",
                    encoding="utf-8",
                )
                retried = await orchestrator.handle_line("/retry")
                return failed.output or "", retried.output or ""

            failed_output, retried_output = asyncio.run(run())
            self.assertIn("passed=False", failed_output)
            self.assertIn("passed=True", retried_output)
            self.assertIsNone(session.last_failed_action)

    def test_rollback_restores_latest_snapshot_without_git(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "notes.txt").write_text("before\n", encoding="utf-8")
            registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
            health = ProviderHealthService(registry, AdapterFactory())
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            context_manager = ContextManager(temp_path)
            approvals = ApprovalManager()
            orchestrator = Orchestrator(
                session=session,
                runtime_state=runtime_state,
                provider_registry=registry,
                broker=PolicyDrivenBroker(registry, health),
                health_service=health,
                adapter_factory=AdapterFactory(),
                context_manager=context_manager,
                context_composer=DefaultContextComposer(
                    context_manager,
                    session,
                    runtime_state,
                    ProjectManifest(project_id="temp-rollback"),
                ),
                event_bus=EventBus(sinks=[]),
                patch_service=PatchService(WorkspaceFiles(temp_path, temp_path / ".artifacts")),
                approval_manager=approvals,
            )

            async def run() -> str:
                blocked = await orchestrator.handle_line('/replace notes.txt "before" "after"')
                approval_id = blocked.output.split("Approval required: ", 1)[1].splitlines()[0]
                await orchestrator.handle_line(f"/approve {approval_id}")
                rolled_back = await orchestrator.handle_line("/rollback latest")
                return rolled_back.output or ""

            output = asyncio.run(run())
            self.assertIn("Rolled back patch: notes.txt", output)
            self.assertEqual((temp_path / "notes.txt").read_text(encoding="utf-8"), "before\n")

    def test_autoedit_generates_plan_and_applies_after_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "notes.txt").write_text("before\n", encoding="utf-8")
            registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
            adapter_factory = ScriptedAdapterFactory(
                json.dumps(
                    {
                        "edits": [
                            {
                                "path": "notes.txt",
                                "old": "before",
                                "new": "after",
                                "reason": "apply requested rename",
                            }
                        ]
                    }
                )
            )
            health = ProviderHealthService(registry, adapter_factory)
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            context_manager = ContextManager(temp_path)
            approvals = ApprovalManager()
            orchestrator = Orchestrator(
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
                    ProjectManifest(project_id="temp-autoedit"),
                ),
                event_bus=EventBus(sinks=[]),
                patch_service=PatchService(WorkspaceFiles(temp_path, temp_path / ".artifacts")),
                approval_manager=approvals,
            )

            async def run() -> tuple[str, str]:
                await orchestrator.handle_line("/add notes.txt")
                planned = await orchestrator.handle_line('/autoedit "change before to after"')
                approval_id = planned.output.split("Approval required: ", 1)[1].splitlines()[0]
                approved = await orchestrator.handle_line(f"/approve {approval_id}")
                return planned.output or "", approved.output or ""

            planned_output, approved_output = asyncio.run(run())
            self.assertIn("planned_edits=1", planned_output)
            self.assertIn("notes.txt (apply requested rename)", planned_output)
            self.assertIn("applied_edits=1", approved_output)
            self.assertEqual((temp_path / "notes.txt").read_text(encoding="utf-8"), "after\n")

    def test_autoedit_rolls_back_partial_batch_on_apply_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "one.txt").write_text("alpha\n", encoding="utf-8")
            (temp_path / "two.txt").write_text("beta\n", encoding="utf-8")
            registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
            adapter_factory = ScriptedAdapterFactory(
                json.dumps(
                    {
                        "edits": [
                            {
                                "path": "one.txt",
                                "old": "alpha",
                                "new": "gamma",
                                "reason": "first edit",
                            },
                            {
                                "path": "two.txt",
                                "old": "missing",
                                "new": "delta",
                                "reason": "second edit fails",
                            },
                        ]
                    }
                )
            )
            health = ProviderHealthService(registry, adapter_factory)
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            context_manager = ContextManager(temp_path)
            approvals = ApprovalManager()
            orchestrator = Orchestrator(
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
                    ProjectManifest(project_id="temp-autoedit-rollback"),
                ),
                event_bus=EventBus(sinks=[]),
                patch_service=PatchService(WorkspaceFiles(temp_path, temp_path / ".artifacts")),
                approval_manager=approvals,
            )

            async def run() -> str:
                await orchestrator.handle_line("/add one.txt two.txt")
                planned = await orchestrator.handle_line('/autoedit "apply batch changes"')
                approval_id = planned.output.split("Approval required: ", 1)[1].splitlines()[0]
                approved = await orchestrator.handle_line(f"/approve {approval_id}")
                self.assertTrue(approved.is_error)
                return approved.output or ""

            output = asyncio.run(run())
            self.assertIn("Rolled back 1 already applied edit(s).", output)
            self.assertEqual((temp_path / "one.txt").read_text(encoding="utf-8"), "alpha\n")
            self.assertEqual((temp_path / "two.txt").read_text(encoding="utf-8"), "beta\n")

    def test_orchestrator_diff_and_undo_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            init_git_repo(temp_path)
            (temp_path / "README.md").write_text("changed\n", encoding="utf-8")
            registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
            health = ProviderHealthService(registry, AdapterFactory())
            sink = RecordingSink()
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            context_manager = ContextManager(temp_path)
            orchestrator = Orchestrator(
                session=session,
                runtime_state=runtime_state,
                provider_registry=registry,
                broker=PolicyDrivenBroker(registry, health),
                health_service=health,
                adapter_factory=AdapterFactory(),
                context_manager=context_manager,
                context_composer=DefaultContextComposer(
                    context_manager,
                    session,
                    runtime_state,
                    ProjectManifest(project_id="temp-repo"),
                ),
                event_bus=EventBus(sinks=[sink]),
                git_workspace=GitWorkspace(temp_path),
            )

            async def run() -> tuple[str, str]:
                diff_result = await orchestrator.handle_line("/diff README.md")
                undo_result = await orchestrator.handle_line("/undo README.md")
                return diff_result.output or "", undo_result.output or ""

            diff_output, undo_output = asyncio.run(run())
            self.assertIn("diff:", diff_output)
            self.assertIn("Restored tracked files: README.md", undo_output)


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
