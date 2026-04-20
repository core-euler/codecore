from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")

from codecore.context.composer import DefaultContextComposer
from codecore.context.manager import ContextManager
from codecore.domain.models import ChatMessage, ChatRequest, ChatResult
from codecore.domain.enums import TaskTag
from codecore.infra.manifest_loader import load_project_manifest
from codecore.kernel.event_bus import EventBus
from codecore.kernel.orchestrator import Orchestrator
from codecore.kernel.runtime_state import RuntimeState
from codecore.kernel.session import SessionRuntime, new_session_runtime
from codecore.memory.recall import MemoryRecallComposer
from codecore.memory.store import SQLiteMemoryStore
from codecore.providers.adapters.base import AdapterFactory
from codecore.providers.broker import PolicyDrivenBroker
from codecore.providers.capabilities import route_capabilities
from codecore.providers.health import ProviderHealthService
from codecore.providers.registry import ProviderRegistry
from codecore.telemetry.analytics import TelemetryAnalytics
from codecore.telemetry.tracker import TelemetryTracker
from codecore.infra.manifest_loader import load_provider_registry


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


class TelemetryProjectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self._previous_deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")
        os.environ["DEEPSEEK_API_KEY"] = "test-key"

    def tearDown(self) -> None:
        if self._previous_deepseek_api_key is None:
            os.environ.pop("DEEPSEEK_API_KEY", None)
        else:
            os.environ["DEEPSEEK_API_KEY"] = self._previous_deepseek_api_key

    def test_prompt_writes_request_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tracker = TelemetryTracker(temp_path / "registry.db", temp_path / "events")
            memory_store = SQLiteMemoryStore(temp_path / "registry.db")
            session = new_session_runtime()
            session.task_tag = TaskTag.GENERAL
            runtime_state = RuntimeState.default()
            registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
            adapter_factory = ScriptedAdapterFactory(json.dumps({"type": "final", "message": "hello from telemetry"}))
            health = ProviderHealthService(registry, adapter_factory)
            context_manager = ContextManager(ROOT)
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
                    load_project_manifest(ROOT / ".codecore" / "project.yaml"),
                ),
                event_bus=EventBus(sinks=[tracker, memory_store]),
            )

            async def run() -> None:
                await orchestrator.start()
                await orchestrator.handle_line("hello from telemetry")
                await orchestrator.stop()

            asyncio.run(run())

            conn = sqlite3.connect(temp_path / "registry.db")
            request_count = conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
            session_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            self.assertEqual(session_count, 1)
            self.assertEqual(request_count, 1)

    def test_rate_updates_request_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tracker = TelemetryTracker(temp_path / "registry.db", temp_path / "events")
            memory_store = SQLiteMemoryStore(temp_path / "registry.db")
            session = new_session_runtime()
            session.task_tag = TaskTag.GENERAL
            runtime_state = RuntimeState.default()
            registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
            adapter_factory = ScriptedAdapterFactory(json.dumps({"type": "final", "message": "hello from telemetry"}))
            health = ProviderHealthService(registry, adapter_factory)
            context_manager = ContextManager(ROOT)
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
                    load_project_manifest(ROOT / ".codecore" / "project.yaml"),
                ),
                event_bus=EventBus(sinks=[tracker, memory_store]),
            )

            async def run() -> None:
                await orchestrator.start()
                await orchestrator.handle_line("hello from telemetry")
                await orchestrator.handle_line("/rate 5")
                await orchestrator.stop()

            asyncio.run(run())

            conn = sqlite3.connect(temp_path / "registry.db")
            rating = conn.execute("SELECT rating FROM requests").fetchone()[0]
            self.assertEqual(rating, 5)

    def test_memory_recall_is_injected_into_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tracker = TelemetryTracker(temp_path / "registry.db", temp_path / "events")
            memory_store = SQLiteMemoryStore(temp_path / "registry.db")
            session = new_session_runtime()
            session.task_tag = TaskTag.REVIEW
            runtime_state = RuntimeState.default()
            registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
            adapter_factory = ScriptedAdapterFactory(
                json.dumps({"type": "final", "message": "Review result for backend contract changes."})
            )
            health = ProviderHealthService(registry, adapter_factory)
            context_manager = ContextManager(ROOT)
            manifest = load_project_manifest(ROOT / ".codecore" / "project.yaml")
            composer = DefaultContextComposer(
                context_manager,
                session,
                runtime_state,
                manifest,
                memory_recall_composer=MemoryRecallComposer(memory_store),
            )
            orchestrator = Orchestrator(
                session=session,
                runtime_state=runtime_state,
                provider_registry=registry,
                broker=PolicyDrivenBroker(registry, health),
                health_service=health,
                adapter_factory=adapter_factory,
                context_manager=context_manager,
                context_composer=composer,
                event_bus=EventBus(sinks=[tracker, memory_store]),
            )

            async def run() -> str:
                await orchestrator.start()
                await orchestrator.handle_line("Need review findings for backend contract changes")
                await orchestrator.handle_line("/rate 5")
                request = ChatRequest(
                    messages=(ChatMessage(role="user", content="Need review findings for backend contract changes"),),
                    task_tag=TaskTag.REVIEW,
                )
                composed = await composer.compose(request)
                await orchestrator.stop()
                return composed.system_prompt

            prompt = asyncio.run(run())
            self.assertIn("Relevant memory:", prompt)
            self.assertIn("turn.outcome", prompt)

    def test_stats_command_renders_analytics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tracker = TelemetryTracker(temp_path / "registry.db", temp_path / "events")
            memory_store = SQLiteMemoryStore(temp_path / "registry.db")
            analytics = TelemetryAnalytics(temp_path / "registry.db", temp_path / "events")
            session = new_session_runtime()
            session.task_tag = TaskTag.REVIEW
            runtime_state = RuntimeState.default()
            registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
            adapter_factory = ScriptedAdapterFactory(
                json.dumps({"type": "final", "message": "Review result for backend contract changes."})
            )
            health = ProviderHealthService(registry, adapter_factory)
            context_manager = ContextManager(ROOT)
            manifest = load_project_manifest(ROOT / ".codecore" / "project.yaml")
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
                    manifest,
                    memory_recall_composer=MemoryRecallComposer(memory_store),
                ),
                event_bus=EventBus(sinks=[tracker, memory_store]),
                analytics_service=analytics,
            )

            async def run() -> str:
                await orchestrator.start()
                await orchestrator.handle_line("Need review findings for backend contract changes")
                await orchestrator.handle_line("/rate 4")
                result = await orchestrator.handle_line("/stats")
                await orchestrator.stop()
                return result.output or ""

            output = asyncio.run(run())
            self.assertIn("overview:", output)
            self.assertIn("memory:", output)
            self.assertIn("recommendation:", output)
            self.assertIn("model_rankings:", output)
            self.assertIn("route_rankings:", output)
            self.assertIn("memory_patterns:", output)
            self.assertIn("provider_reliability:", output)


if __name__ == "__main__":
    unittest.main()
