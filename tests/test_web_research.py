from __future__ import annotations

import asyncio
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
from codecore.infra.manifest_loader import load_provider_registry
from codecore.infra.project_manifest import ProjectManifest
from codecore.infra.web_research import ProofRecord, SearchResult, WebResearchService
from codecore.kernel.event_bus import EventBus
from codecore.kernel.orchestrator import Orchestrator
from codecore.kernel.runtime_state import RuntimeState
from codecore.kernel.session import new_session_runtime
from codecore.providers.adapters.base import AdapterFactory
from codecore.providers.broker import PolicyDrivenBroker
from codecore.providers.health import ProviderHealthService
from codecore.providers.registry import ProviderRegistry


class WebResearchServiceTest(unittest.TestCase):
    def test_search_parses_duckduckgo_results(self) -> None:
        html = """
        <a class="result__a" href="https://example.com/docs">Example Docs</a>
        <a class="result__snippet">Current middleware guidance.</a>
        """
        service = WebResearchService(fetch_text=lambda url: html, fetch_json=lambda url: {})

        results = service.search("middleware")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Example Docs")
        self.assertEqual(results[0].url, "https://example.com/docs")
        self.assertIn("middleware guidance", results[0].snippet)

    def test_docs_reads_pypi_metadata(self) -> None:
        payload = {
            "info": {
                "version": "0.115.0",
                "project_urls": {"Documentation": "https://fastapi.tiangolo.com/"},
            }
        }
        service = WebResearchService(fetch_text=lambda url: "", fetch_json=lambda url: payload)

        result = service.docs("fastapi")

        self.assertEqual(result.latest, "0.115.0")
        self.assertEqual(result.docs_url, "https://fastapi.tiangolo.com/")

    def test_inspect_dependencies_reads_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "pyproject.toml").write_text(
                "[project]\ndependencies = ['fastapi==0.95.0', 'rich>=14.0,<15']\n",
                encoding="utf-8",
            )

            versions = {
                "fastapi": {"info": {"version": "0.115.0", "project_urls": {}}},
                "rich": {"info": {"version": "14.2.0", "project_urls": {}}},
            }
            service = WebResearchService(fetch_text=lambda url: "", fetch_json=lambda url: versions[url.split('/')[-2]])

            results = service.inspect_dependencies(temp_path)

            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].package, "fastapi")
            self.assertEqual(results[0].status, "major-gap")
            self.assertEqual(results[1].status, "range")


class _FakeWebResearchService:
    def search(self, query: str, *, limit: int = 5):
        return (SearchResult(title="Docs", url="https://example.com", snippet="Verified result"),)

    def verify(self, claim: str, *, limit: int = 3):
        return (ProofRecord(claim=claim, title="Docs", url="https://example.com", snippet="Verified result", checked_at="2026-04-02"),)

    def docs(self, package: str):
        return type("Docs", (), {"package": package, "latest": "1.2.3", "docs_url": "https://example.com/docs"})()

    def inspect_dependencies(self, project_root: Path):
        return (
            type("Dep", (), {"package": "fastapi", "used": "fastapi==0.95.0", "latest": "0.115.0", "status": "major-gap"})(),
        )


class WebResearchCommandTest(unittest.TestCase):
    def test_verify_and_proofs_commands_store_session_proofs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = ProviderRegistry(load_provider_registry(ROOT / ".codecore" / "providers" / "registry.yaml"))
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
                    ProjectManifest(project_id="web-test"),
                ),
                event_bus=EventBus(sinks=[]),
                web_research_service=_FakeWebResearchService(),
            )

            async def run():
                verified = await orchestrator.handle_line("/verify fastapi lifespan pattern")
                proofs = await orchestrator.handle_line("/proofs")
                docs = await orchestrator.handle_line("/docs fastapi")
                deps = await orchestrator.handle_line("/deps")
                return verified, proofs, docs, deps

            verified, proofs, docs, deps = asyncio.run(run())

            self.assertIn("[proof] Claim:", verified.output)
            self.assertIn("fastapi lifespan pattern", proofs.output)
            self.assertIn("latest=1.2.3", docs.output)
            self.assertIn("fastapi | fastapi==0.95.0 | 0.115.0 | major-gap", deps.output)
