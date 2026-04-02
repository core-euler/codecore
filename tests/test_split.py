from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codecore.kernel.command_router import CommandResult
from codecore.kernel.runtime_state import RuntimeState
from codecore.kernel.session import new_session_runtime
from codecore.split import SplitCoordinator, SplitRoleRuntime


class _StubOrchestrator:
    def __init__(self, role: str) -> None:
        self.role = role
        self.session = new_session_runtime()
        self.runtime_state = RuntimeState.default()
        self.approval_manager = None
        self.context_manager = SimpleNamespace(project_root=ROOT)
        self.calls: list[str] = []

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def handle_line(self, line: str) -> CommandResult:
        self.calls.append(line)
        if line == "/exit":
            return CommandResult(output=f"{self.role} exit", should_exit=True)
        self.session.last_model_alias = "mock"
        self.session.request_count += 1
        self.session.transcript.append(SimpleNamespace(role="assistant", content=f"{self.role}: {line}"))
        return CommandResult(output=f"{self.role}: {line}", render_mode="markdown")


class SplitCoordinatorTest(unittest.TestCase):
    def test_send_uses_last_architect_message_and_records_hook(self) -> None:
        architect = _StubOrchestrator("architect")
        architect.session.transcript.append(SimpleNamespace(role="assistant", content="Implement auth middleware"))
        executor = _StubOrchestrator("executor")
        coordinator = SplitCoordinator(
            architect=SplitRoleRuntime(role="architect", orchestrator=architect),
            executor=SplitRoleRuntime(role="executor", orchestrator=executor),
        )

        async def run():
            return await coordinator.handle_line("/send")

        result = asyncio.run(run())

        self.assertIn("[executor] executor: ## Task", result.output)
        self.assertIn("Implement auth middleware", executor.calls[0])
        self.assertIn("Default mode is incremental", executor.calls[0])
        self.assertIsNotNone(coordinator.last_hook)
        self.assertIn('"status": "complete"', coordinator.last_hook)
        self.assertEqual(coordinator.active_role, "architect")

    def test_mode_switch_changes_executor_prompt(self) -> None:
        architect = _StubOrchestrator("architect")
        architect.session.transcript.append(SimpleNamespace(role="assistant", content="Rebuild auth module"))
        architect.session.recent_proofs.append(
            {
                "title": "FastAPI Docs",
                "url": "https://fastapi.tiangolo.com/",
                "snippet": "Use lifespan for startup and shutdown logic.",
            }
        )
        executor = _StubOrchestrator("executor")
        coordinator = SplitCoordinator(
            architect=SplitRoleRuntime(role="architect", orchestrator=architect),
            executor=SplitRoleRuntime(role="executor", orchestrator=executor),
        )

        async def run():
            mode_result = await coordinator.handle_line("/mode rebuild")
            send_result = await coordinator.handle_line("/send")
            return mode_result, send_result

        mode_result, send_result = asyncio.run(run())

        self.assertIn("Split mode set to rebuild.", mode_result.output)
        self.assertEqual(coordinator.execution_mode, "rebuild")
        self.assertIn("Source of truth: documentation, tests, and verified facts from Architect.", executor.calls[0])
        self.assertIn("## Verified Facts", executor.calls[0])
        self.assertIn("https://fastapi.tiangolo.com/", executor.calls[0])
        self.assertIn('"mode": "rebuild"', send_result.output)

    def test_render_overview_includes_mode(self) -> None:
        coordinator = SplitCoordinator(
            architect=SplitRoleRuntime(role="architect", orchestrator=_StubOrchestrator("architect")),
            executor=SplitRoleRuntime(role="executor", orchestrator=_StubOrchestrator("executor")),
        )
        overview = coordinator.render_overview()
        self.assertIn("execution: `incremental`", overview)

    def test_architect_blocks_mutating_commands(self) -> None:
        coordinator = SplitCoordinator(
            architect=SplitRoleRuntime(role="architect", orchestrator=_StubOrchestrator("architect")),
            executor=SplitRoleRuntime(role="executor", orchestrator=_StubOrchestrator("executor")),
        )

        async def run():
            return await coordinator.handle_line("/apply")

        result = asyncio.run(run())

        self.assertTrue(result.is_error)
        self.assertIn("read-only", result.output)

    def test_focus_switches_roles(self) -> None:
        coordinator = SplitCoordinator(
            architect=SplitRoleRuntime(role="architect", orchestrator=_StubOrchestrator("architect")),
            executor=SplitRoleRuntime(role="executor", orchestrator=_StubOrchestrator("executor")),
        )

        async def run():
            await coordinator.handle_line("/focus executor")
            return await coordinator.handle_line("hello")

        result = asyncio.run(run())

        self.assertEqual(coordinator.active_role, "executor")
        self.assertIn("[executor] executor: hello", result.output)

    def test_executor_blocks_research_commands(self) -> None:
        coordinator = SplitCoordinator(
            architect=SplitRoleRuntime(role="architect", orchestrator=_StubOrchestrator("architect")),
            executor=SplitRoleRuntime(role="executor", orchestrator=_StubOrchestrator("executor")),
            active_role="executor",
        )

        async def run():
            return await coordinator.handle_line("/search fastapi lifespan")

        result = asyncio.run(run())

        self.assertTrue(result.is_error)
        self.assertIn("reserved for Architect", result.output)


class SplitEntryPointSmokeTest(unittest.TestCase):
    def test_module_entrypoint_runs_in_split_mode(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "codecore", "--split"],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(SRC)},
            input="/exit\n",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("mode=split/incremental", proc.stdout)
        self.assertIn("[architect] Session finished.", proc.stdout)

    def test_module_entrypoint_accepts_rebuild_mode(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "codecore", "--split", "--mode", "rebuild"],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(SRC)},
            input="/exit\n",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("mode=split/rebuild", proc.stdout)
