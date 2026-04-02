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
from codecore.infra.knowledge_base import KnowledgeBaseStore
from codecore.infra.manifest_loader import load_project_manifest, load_provider_registry
from codecore.kernel.event_bus import EventBus
from codecore.kernel.orchestrator import Orchestrator
from codecore.kernel.runtime_state import RuntimeState
from codecore.kernel.session import new_session_runtime
from codecore.providers.adapters.base import AdapterFactory
from codecore.providers.broker import PolicyDrivenBroker
from codecore.providers.health import ProviderHealthService
from codecore.providers.registry import ProviderRegistry


class KnowledgeBaseStoreTest(unittest.TestCase):
    def test_init_and_index_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = KnowledgeBaseStore(root, root / ".codecore", root / ".codecore" / "knowledge" / "index.json")

            created = store.init_structure()
            documents = store.load_documents()

            self.assertTrue(created)
            self.assertTrue((root / "docs" / "spec.md").exists())
            self.assertTrue(store.index_path.exists())
            self.assertTrue(any(item.path == "docs/spec.md" for item in documents))

    def test_add_document_indexes_existing_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs_dir = root / "docs"
            docs_dir.mkdir(parents=True)
            target = docs_dir / "custom.md"
            target.write_text("# Custom Doc\n\nBody\n", encoding="utf-8")
            store = KnowledgeBaseStore(root, root / ".codecore", root / ".codecore" / "knowledge" / "index.json")

            entry = store.add_document("docs/custom.md")

            self.assertEqual(entry.doc_id, "custom")
            self.assertEqual(entry.path, "docs/custom.md")

    def test_complete_phase_creates_result_doc_and_reindexes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = KnowledgeBaseStore(root, root / ".codecore", root / ".codecore" / "knowledge" / "index.json")

            result_path = store.complete_phase("phase-2")
            docs = store.load_documents()

            self.assertTrue(result_path.exists())
            self.assertTrue(any(item.path == "docs/results/phase-2-result.md" for item in docs))

    def test_lookup_returns_relevant_excerpt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            docs_dir = root / "docs"
            docs_dir.mkdir(parents=True)
            (docs_dir / "spec.md").write_text("# Spec\n\nJWT auth middleware is required.\n", encoding="utf-8")
            (docs_dir / "notes.md").write_text("# Notes\n\nUnrelated content.\n", encoding="utf-8")
            store = KnowledgeBaseStore(root, root / ".codecore", root / ".codecore" / "knowledge" / "index.json")

            store.index_docs()
            matches = store.lookup("jwt auth")

            self.assertTrue(matches)
            self.assertEqual(matches[0].doc_id, "spec")
            self.assertIn("JWT auth middleware", matches[0].excerpt)


class KnowledgeBaseCommandTest(unittest.TestCase):
    def test_kb_commands_init_index_show_and_add(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = ProviderRegistry(load_provider_registry(ROOT / ".codecore" / "providers" / "registry.yaml"))
            health = ProviderHealthService(registry, AdapterFactory())
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            context_manager = ContextManager(temp_path)
            knowledge_store = KnowledgeBaseStore(
                temp_path,
                temp_path / ".codecore",
                temp_path / ".codecore" / "knowledge" / "index.json",
            )
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
                knowledge_base_store=knowledge_store,
            )

            async def run():
                created = await orchestrator.handle_line("/kb init")
                indexed = await orchestrator.handle_line("/kb index")
                shown = await orchestrator.handle_line("/kb show")
                added = await orchestrator.handle_line("/kb add docs/spec.md")
                return created, indexed, shown, added

            created, indexed, shown, added = asyncio.run(run())

            self.assertIn("Initialized knowledge base", created.output)
            self.assertIn("Indexed", indexed.output)
            self.assertIn("docs/spec.md", shown.output)
            self.assertIn("Indexed spec", added.output)

    def test_complete_command_creates_result_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = ProviderRegistry(load_provider_registry(ROOT / ".codecore" / "providers" / "registry.yaml"))
            health = ProviderHealthService(registry, AdapterFactory())
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            context_manager = ContextManager(temp_path)
            knowledge_store = KnowledgeBaseStore(
                temp_path,
                temp_path / ".codecore",
                temp_path / ".codecore" / "knowledge" / "index.json",
            )
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
                knowledge_base_store=knowledge_store,
            )

            async def run():
                return await orchestrator.handle_line("/complete phase-2")

            result = asyncio.run(run())

            self.assertIn("docs/results/phase-2-result.md", result.output)

    def test_kb_lookup_returns_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            docs_dir = temp_path / "docs"
            docs_dir.mkdir(parents=True)
            (docs_dir / "spec.md").write_text("# Spec\n\nCurrent auth flow uses JWT.\n", encoding="utf-8")
            registry = ProviderRegistry(load_provider_registry(ROOT / ".codecore" / "providers" / "registry.yaml"))
            health = ProviderHealthService(registry, AdapterFactory())
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            context_manager = ContextManager(temp_path)
            knowledge_store = KnowledgeBaseStore(
                temp_path,
                temp_path / ".codecore",
                temp_path / ".codecore" / "knowledge" / "index.json",
            )
            knowledge_store.index_docs()
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
                knowledge_base_store=knowledge_store,
            )

            async def run():
                return await orchestrator.handle_line("/kb lookup jwt")

            result = asyncio.run(run())

            self.assertIn("Knowledge matches:", result.output)
            self.assertIn("docs/spec.md", result.output)
