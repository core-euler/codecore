from __future__ import annotations

import asyncio
import os
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codecore.context.composer import DefaultContextComposer
from codecore.context.manager import ContextManager
from codecore.infra.manifest_loader import load_project_manifest, load_provider_registry
from codecore.domain.enums import TaskTag
from codecore.domain.events import EventEnvelope
from codecore.domain.models import ChatMessage, ChatRequest
from codecore.kernel.event_bus import EventBus
from codecore.kernel.orchestrator import Orchestrator
from codecore.kernel.runtime_state import RuntimeState
from codecore.kernel.session import new_session_runtime
from codecore.providers.adapters.base import AdapterFactory
from codecore.providers.broker import PolicyDrivenBroker
from codecore.providers.health import ProviderHealthService
from codecore.providers.registry import ProviderRegistry


class RecordingSink:
    def __init__(self) -> None:
        self.events: list[EventEnvelope] = []

    async def publish(self, event: EventEnvelope) -> None:
        self.events.append(event)


class HealthyFailingAdapter:
    def __init__(self, route) -> None:
        self._route = route

    async def chat(self, request):
        if self._route.provider_id == "mock":
            prompt = request.messages[-1].content
            from codecore.domain.models import ChatResult

            return ChatResult(text=f"[mock:{self._route.alias}] {prompt}", latency_ms=7)
        raise RuntimeError(f"simulated failure for {self._route.provider_id}")

    async def stream(self, request):
        yield (await self.chat(request)).text

    async def health(self):
        from codecore.domain.enums import HealthState
        from codecore.domain.models import HealthStatus

        return HealthStatus(state=HealthState.HEALTHY, checked_at=HealthStatus.unknown().checked_at, detail="ok")

    def capabilities(self):
        from codecore.providers.capabilities import route_capabilities

        return route_capabilities(self._route)


class FailingAdapterFactory:
    def create(self, route):
        return HealthyFailingAdapter(route)


class ProviderBrokerTest(unittest.TestCase):
    def test_broker_falls_back_to_mock_without_keys(self) -> None:
        registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
        health = ProviderHealthService(registry, AdapterFactory())
        broker = PolicyDrivenBroker(registry, health)

        async def run() -> str:
            route = await broker.select_route(
                ChatRequest(messages=(ChatMessage(role="user", content="hello"),), task_tag=TaskTag.GENERAL)
            )
            return route.alias or route.model_id

        alias = asyncio.run(run())
        self.assertEqual(alias, "mock")

    def test_orchestrator_retries_next_route_on_model_error(self) -> None:
        registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
        adapter_factory = FailingAdapterFactory()
        health = ProviderHealthService(registry, adapter_factory)
        sink = RecordingSink()
        session = new_session_runtime()
        session.task_tag = TaskTag.GENERAL
        runtime_state = RuntimeState.default()
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
            event_bus=EventBus(sinks=[sink]),
        )

        async def run() -> str:
            await orchestrator.start()
            result = await orchestrator.handle_line("retry please")
            await orchestrator.stop()
            self.assertFalse(result.is_error)
            return result.output or ""

        with patch.dict(
            os.environ,
            {
                "DEEPSEEK_API_KEY": "test-key",
                "MISTRAL_API_KEY": "test-key",
                "OPENROUTER_API_KEY": "test-key",
            },
            clear=False,
        ):
            output = asyncio.run(run())
        fallback_events = [event for event in sink.events if event.kind.value == "fallback.triggered"]
        self.assertIn("[mock:mock] retry please", output)
        self.assertGreaterEqual(len(fallback_events), 1)
        self.assertEqual(session.last_model_alias, "mock")

    def test_broker_prefers_project_alias_order(self) -> None:
        registry = ProviderRegistry(load_provider_registry(ROOT / "providers" / "registry.yaml"))
        health = ProviderHealthService(registry, FailingAdapterFactory())
        broker = PolicyDrivenBroker(registry, health, preferred_aliases=("codestral",), allow_vpn_routes=False)

        async def run() -> str:
            route = await broker.select_route(
                ChatRequest(messages=(ChatMessage(role="user", content="pick backend"),), task_tag=TaskTag.CODE)
            )
            return route.alias or route.model_id

        with patch.dict(
            os.environ,
            {
                "DEEPSEEK_API_KEY": "test-key",
                "MISTRAL_API_KEY": "test-key",
                "OPENROUTER_API_KEY": "test-key",
            },
            clear=False,
        ):
            alias = asyncio.run(run())
        self.assertEqual(alias, "codestral")


if __name__ == "__main__":
    unittest.main()
