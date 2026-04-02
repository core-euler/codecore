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
from codecore.infra.aidd_docs import AIDDDocsStore
from codecore.infra.manifest_loader import load_project_manifest, load_provider_registry
from codecore.kernel.event_bus import EventBus
from codecore.kernel.orchestrator import Orchestrator
from codecore.kernel.runtime_state import RuntimeState
from codecore.kernel.session import new_session_runtime
from codecore.providers.adapters.base import AdapterFactory
from codecore.providers.broker import PolicyDrivenBroker
from codecore.providers.health import ProviderHealthService
from codecore.providers.registry import ProviderRegistry


class AIDDDocsStoreTest(unittest.TestCase):
    def test_add_list_and_close_issue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = AIDDDocsStore(root)

            entry = store.add_issue("Auth returns 500 on expired token")
            open_issues = store.list_issues()
            closed = store.close_issue(entry.entry_id, "Handle ExpiredSignatureError separately")
            after_close = store.list_issues()

            self.assertEqual(entry.entry_id, "ISSUE-001")
            self.assertEqual(len(open_issues), 1)
            self.assertEqual(closed.status, "Resolved")
            self.assertEqual(after_close, ())

    def test_add_list_and_search_antipatterns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = AIDDDocsStore(root)

            entry = store.add_antipattern("ModuleNotFoundError: aiogram\nFile \"bot/main.py\", line 3")
            entries = store.list_antipatterns()
            matches = store.search_antipatterns("aiogram")

            self.assertEqual(entry.entry_id, "AP-001")
            self.assertEqual(len(entries), 1)
            self.assertEqual(matches[0].entry_id, "AP-001")


class AIDDDocsCommandTest(unittest.TestCase):
    def test_issue_and_ap_commands_write_markdown_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = ProviderRegistry(load_provider_registry(ROOT / ".codecore" / "providers" / "registry.yaml"))
            health = ProviderHealthService(registry, AdapterFactory())
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            context_manager = ContextManager(temp_path)
            docs_store = AIDDDocsStore(temp_path)
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
                aidd_docs_store=docs_store,
            )

            async def run():
                created_issue = await orchestrator.handle_line('/issue "Auth returns 500 on expired token"')
                listed_issues = await orchestrator.handle_line("/issue list")
                closed_issue = await orchestrator.handle_line('/issue close ISSUE-001 "Return 401 instead of 500"')
                recorded_ap = await orchestrator.handle_line('/ap "ModuleNotFoundError: aiogram"')
                searched_ap = await orchestrator.handle_line("/ap search aiogram")
                return created_issue, listed_issues, closed_issue, recorded_ap, searched_ap

            created_issue, listed_issues, closed_issue, recorded_ap, searched_ap = asyncio.run(run())

            self.assertIn("Created ISSUE-001", created_issue.output)
            self.assertIn("ISSUE-001", listed_issues.output)
            self.assertIn("Closed ISSUE-001", closed_issue.output)
            self.assertIn("Recorded AP-001", recorded_ap.output)
            self.assertIn("AP-001", searched_ap.output)
            self.assertIn("ISSUE-001", docs_store.issues_path.read_text(encoding="utf-8"))
            self.assertIn("AP-001", docs_store.antipatterns_path.read_text(encoding="utf-8"))
