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
from codecore.domain.enums import TaskTag
from codecore.domain.models import ChatMessage, ChatRequest
from codecore.infra.manifest_loader import load_project_manifest, load_provider_registry
from codecore.infra.session_state import SessionStateStore
from codecore.kernel.event_bus import EventBus
from codecore.kernel.orchestrator import Orchestrator
from codecore.kernel.runtime_state import RuntimeState
from codecore.kernel.session import new_session_runtime
from codecore.providers.adapters.base import AdapterFactory
from codecore.providers.broker import PolicyDrivenBroker
from codecore.providers.health import ProviderHealthService
from codecore.providers.registry import ProviderRegistry


class SessionStateStoreTest(unittest.TestCase):
    def test_render_and_parse_markdown_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = SessionStateStore(root / "session.json", root / "context.md", root / "snapshots")
            session = new_session_runtime()
            session.transcript = [
                ChatMessage(role="user", content="Нужен auth модуль"),
                ChatMessage(role="assistant", content="Сделаю без refresh tokens."),
            ]

            markdown = store.render_markdown(session)
            parsed = store.parse_markdown(markdown)

            self.assertEqual(parsed, session.transcript)

    def test_save_and_restore_session_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = SessionStateStore(root / "session.json", root / "context.md", root / "snapshots")
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            session.task_tag = TaskTag.DEBUG
            session.transcript = [ChatMessage(role="user", content="debug this")]
            session.active_files = ["src/app.py"]
            session.allowed_action_types = ["run"]
            runtime_state.manual_model_alias = "ds-v3"
            runtime_state.active_skills = ["review"]

            store.save(session, runtime_state)

            restored_session = new_session_runtime()
            restored_runtime_state = RuntimeState.default()
            loaded = store.load_into(restored_session, restored_runtime_state)

            self.assertTrue(loaded)
            self.assertEqual(restored_session.task_tag, TaskTag.DEBUG)
            self.assertEqual(restored_session.transcript[0].content, "debug this")
            self.assertEqual(restored_session.active_files, ["src/app.py"])
            self.assertEqual(restored_runtime_state.manual_model_alias, "ds-v3")
            self.assertEqual(restored_runtime_state.active_skills, ["review"])


class _EditableStore(SessionStateStore):
    def edit_context(self, session, *, editor=None):
        return [
            ChatMessage(role="user", content="edited question"),
            ChatMessage(role="assistant", content="edited answer"),
        ]


class ContextCommandTest(unittest.TestCase):
    def test_ctx_commands_trim_save_load_and_edit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            registry = ProviderRegistry(load_provider_registry(ROOT / ".codecore" / "providers" / "registry.yaml"))
            health = ProviderHealthService(registry, AdapterFactory())
            session = new_session_runtime()
            session.transcript = [
                ChatMessage(role="user", content="first"),
                ChatMessage(role="assistant", content="second"),
                ChatMessage(role="user", content="third"),
            ]
            runtime_state = RuntimeState.default()
            context_manager = ContextManager(temp_path)
            store = _EditableStore(temp_path / ".codecore" / "session.json", temp_path / ".codecore" / "context.md", temp_path / ".codecore" / "snapshots")
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
                session_store=store,
            )

            async def run():
                trimmed = await orchestrator.handle_line("/ctx trim last")
                saved = await orchestrator.handle_line("/ctx save before-auth")
                cleared = await orchestrator.handle_line("/ctx clear")
                loaded = await orchestrator.handle_line("/ctx load before-auth")
                edited = await orchestrator.handle_line("/ctx edit")
                shown = await orchestrator.handle_line("/ctx show")
                return trimmed, saved, cleared, loaded, edited, shown

            trimmed, saved, cleared, loaded, edited, shown = asyncio.run(run())

            self.assertIn("Removed the last exchange", trimmed.output)
            self.assertIn("Saved context snapshot: before-auth", saved.output)
            self.assertIn("Cleared transcript context.", cleared.output)
            self.assertIn("Loaded context snapshot: before-auth", loaded.output)
            self.assertIn("Context updated from editor.", edited.output)
            self.assertIn("edited question", shown.output)

    def test_composer_accounts_for_transcript_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            session = new_session_runtime()
            session.transcript = [
                ChatMessage(role="user", content="Explain the service layout"),
                ChatMessage(role="assistant", content="It uses router to service to repo."),
            ]
            runtime_state = RuntimeState.default()
            context_manager = ContextManager(temp_path)
            composer = DefaultContextComposer(
                context_manager,
                session,
                runtime_state,
                load_project_manifest(ROOT / ".codecore" / "project.yaml"),
            )
            request = ChatRequest(
                messages=(
                    *tuple(session.transcript),
                    ChatMessage(role="user", content="Current step prompt"),
                ),
                metadata={"latest_prompt": "Need auth middleware"},
            )

            composed = asyncio.run(composer.compose(request))

            self.assertEqual(composed.metadata["transcript_message_count"], 2)
            self.assertEqual(composed.messages[:2], tuple(session.transcript))
