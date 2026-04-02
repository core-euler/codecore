from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from prompt_toolkit.document import Document
from rich.console import Console

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codecore.domain.enums import RiskLevel
from codecore.execution.approvals import ApprovalManager
from codecore.ui.repl import SlashCommandCompleter
from codecore.ui.repl import Repl


class ReplCompletionTest(unittest.TestCase):
    def test_slash_command_completer_lists_commands_for_root_slash(self) -> None:
        completer = SlashCommandCompleter()

        completions = list(completer.get_completions(Document("/"), None))

        texts = {completion.text for completion in completions}
        self.assertIn("help", texts)
        self.assertIn("status", texts)
        self.assertIn("apply", texts)

    def test_slash_command_completer_filters_by_prefix(self) -> None:
        completer = SlashCommandCompleter()

        completions = list(completer.get_completions(Document("/ap"), None))

        texts = {completion.text for completion in completions}
        self.assertIn("apply", texts)
        self.assertIn("approve", texts)
        self.assertNotIn("status", texts)

    def test_slash_command_completer_ignores_plain_text(self) -> None:
        completer = SlashCommandCompleter()

        completions = list(completer.get_completions(Document("hello"), None))

        self.assertEqual(completions, [])

    def test_slash_command_completer_suggests_model_aliases(self) -> None:
        orchestrator = SimpleNamespace(
            provider_registry=SimpleNamespace(
                list_registered=lambda: (
                    SimpleNamespace(model=SimpleNamespace(alias="ds-v3", id="deepseek-chat")),
                    SimpleNamespace(model=SimpleNamespace(alias="codestral", id="codestral-latest")),
                )
            ),
            skill_registry=None,
            approval_manager=None,
            multi_agent_runner=None,
            session=SimpleNamespace(active_files=[]),
            context_manager=SimpleNamespace(project_root=ROOT),
        )
        completer = SlashCommandCompleter(orchestrator)

        completions = list(completer.get_completions(Document("/model d"), None))

        texts = {completion.text for completion in completions}
        self.assertIn("ds-v3", texts)
        self.assertIn("deepseek-chat", texts)

    def test_slash_command_completer_suggests_task_tags(self) -> None:
        completer = SlashCommandCompleter(SimpleNamespace(
            provider_registry=SimpleNamespace(list_registered=lambda: ()),
            skill_registry=None,
            approval_manager=None,
            multi_agent_runner=None,
            session=SimpleNamespace(active_files=[]),
            context_manager=SimpleNamespace(project_root=ROOT),
        ))

        completions = list(completer.get_completions(Document("/tag d"), None))

        texts = {completion.text for completion in completions}
        self.assertIn("debug", texts)

    def test_slash_command_completer_suggests_workspace_files_for_add(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "src").mkdir()
            (temp_path / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
            orchestrator = SimpleNamespace(
                provider_registry=SimpleNamespace(list_registered=lambda: ()),
                skill_registry=None,
                approval_manager=None,
                multi_agent_runner=None,
                session=SimpleNamespace(active_files=[]),
                context_manager=SimpleNamespace(project_root=temp_path),
            )
            completer = SlashCommandCompleter(orchestrator)

            completions = list(completer.get_completions(Document("/add src/"), None))

            texts = {completion.text for completion in completions}
            self.assertIn("src/app.py", texts)

    def test_slash_command_completer_suggests_ctx_actions(self) -> None:
        completer = SlashCommandCompleter(SimpleNamespace(
            provider_registry=SimpleNamespace(list_registered=lambda: ()),
            skill_registry=None,
            approval_manager=None,
            multi_agent_runner=None,
            session=SimpleNamespace(active_files=[]),
            context_manager=SimpleNamespace(project_root=ROOT),
            session_store=SimpleNamespace(list_snapshots=lambda: ("before-auth",)),
            aidd_docs_store=SimpleNamespace(list_issues=lambda include_closed=True: (SimpleNamespace(entry_id="ISSUE-001"),)),
        ))

        completions = list(completer.get_completions(Document("/ctx l"), None))

        texts = {completion.text for completion in completions}
        self.assertIn("load", texts)

    def test_slash_command_completer_suggests_issue_actions(self) -> None:
        completer = SlashCommandCompleter(SimpleNamespace(
            provider_registry=SimpleNamespace(list_registered=lambda: ()),
            skill_registry=None,
            approval_manager=None,
            multi_agent_runner=None,
            session=SimpleNamespace(active_files=[]),
            context_manager=SimpleNamespace(project_root=ROOT),
            session_store=SimpleNamespace(list_snapshots=lambda: ()),
            aidd_docs_store=SimpleNamespace(list_issues=lambda include_closed=True: (SimpleNamespace(entry_id="ISSUE-001"),)),
        ))

        completions = list(completer.get_completions(Document("/issue c"), None))

        texts = {completion.text for completion in completions}
        self.assertIn("close", texts)

    def test_slash_command_completer_suggests_skill_actions(self) -> None:
        completer = SlashCommandCompleter(SimpleNamespace(
            provider_registry=SimpleNamespace(list_registered=lambda: ()),
            skill_registry=SimpleNamespace(skill_ids=lambda: ("discover", "implement")),
            approval_manager=None,
            multi_agent_runner=None,
            session=SimpleNamespace(active_files=[]),
            context_manager=SimpleNamespace(project_root=ROOT),
            session_store=SimpleNamespace(list_snapshots=lambda: ()),
            aidd_docs_store=SimpleNamespace(list_issues=lambda include_closed=True: ()),
        ))

        completions = list(completer.get_completions(Document("/skill l"), None))

        texts = {completion.text for completion in completions}
        self.assertIn("list", texts)
        self.assertIn("load", texts)

    def test_slash_command_completer_suggests_kb_actions(self) -> None:
        completer = SlashCommandCompleter(SimpleNamespace(
            provider_registry=SimpleNamespace(list_registered=lambda: ()),
            skill_registry=None,
            approval_manager=None,
            multi_agent_runner=None,
            session=SimpleNamespace(active_files=[]),
            context_manager=SimpleNamespace(project_root=ROOT),
            session_store=SimpleNamespace(list_snapshots=lambda: ()),
            aidd_docs_store=SimpleNamespace(list_issues=lambda include_closed=True: ()),
            knowledge_base_store=SimpleNamespace(load_documents=lambda: (SimpleNamespace(doc_id="spec", path="docs/spec.md"),)),
        ))

        completions = list(completer.get_completions(Document("/kb e"), None))

        texts = {completion.text for completion in completions}
        self.assertIn("edit", texts)

    def test_slash_command_completer_suggests_mcp_actions(self) -> None:
        completer = SlashCommandCompleter(SimpleNamespace(
            provider_registry=SimpleNamespace(list_registered=lambda: ()),
            skill_registry=None,
            approval_manager=None,
            multi_agent_runner=None,
            session=SimpleNamespace(active_files=[]),
            context_manager=SimpleNamespace(project_root=ROOT),
            session_store=SimpleNamespace(list_snapshots=lambda: ()),
            aidd_docs_store=SimpleNamespace(list_issues=lambda include_closed=True: ()),
            knowledge_base_store=SimpleNamespace(load_documents=lambda: ()),
            mcp_control_plane=SimpleNamespace(list_servers=lambda: (SimpleNamespace(server_id="filesystem"),)),
        ))

        completions = list(completer.get_completions(Document("/mcp d"), None))

        texts = {completion.text for completion in completions}
        self.assertIn("disable", texts)

    def test_slash_command_completer_includes_split_commands_from_runtime(self) -> None:
        completer = SlashCommandCompleter(SimpleNamespace(
            command_specs=(
                SimpleNamespace(name="focus", description="split focus"),
                SimpleNamespace(name="mode", description="split mode"),
                SimpleNamespace(name="research", description="split research"),
            ),
            provider_registry=SimpleNamespace(list_registered=lambda: ()),
            skill_registry=None,
            approval_manager=None,
            multi_agent_runner=None,
            session=SimpleNamespace(active_files=[]),
            context_manager=SimpleNamespace(project_root=ROOT),
        ))

        completions = list(completer.get_completions(Document("/m"), None))

        texts = {completion.text for completion in completions}
        self.assertIn("mode", texts)

    def test_slash_command_completer_suggests_review_paths(self) -> None:
        completer = SlashCommandCompleter(SimpleNamespace(
            command_specs=(),
            provider_registry=SimpleNamespace(list_registered=lambda: ()),
            skill_registry=None,
            approval_manager=None,
            multi_agent_runner=None,
            session=SimpleNamespace(active_files=["src/auth.py"]),
            context_manager=SimpleNamespace(project_root=ROOT),
        ))

        completions = list(completer.get_completions(Document("/review s"), None))

        texts = {completion.text for completion in completions}
        self.assertIn("src/auth.py", texts)


class _GateOrchestrator:
    def __init__(self) -> None:
        self.session = SimpleNamespace(pending_follow_up_action=None)
        self.approval_manager = ApprovalManager()
        self.calls: list[str] = []

    async def handle_line(self, line: str):
        self.calls.append(line)
        if line == "/apply":
            self.session.pending_follow_up_action = None
            return SimpleNamespace(output="planned", should_exit=False, render_mode="text", is_error=False)
        if line == "/dismiss latest":
            latest = self.approval_manager.latest()
            if latest is not None:
                self.approval_manager.dismiss(latest.approval_id)
            return SimpleNamespace(output="dismissed", should_exit=False, render_mode="text", is_error=False)
        raise AssertionError(f"Unexpected line: {line}")


class ReplInteractionGateTest(unittest.TestCase):
    def test_follow_up_gate_triggers_apply_without_prompt(self) -> None:
        orchestrator = _GateOrchestrator()
        orchestrator.session.pending_follow_up_action = "apply_last_prompt"
        seen_titles: list[str] = []

        async def selector(title: str, text: str, options):
            seen_titles.append(title)
            return "apply"

        repl = Repl(orchestrator=orchestrator, console=Console(record=True), modal_selector=selector)

        asyncio.run(repl._resolve_interaction_gate())

        self.assertEqual(orchestrator.calls, ["/apply"])
        self.assertEqual(seen_titles, ["Action Required"])

    def test_approval_gate_requires_modal_choice(self) -> None:
        orchestrator = _GateOrchestrator()
        orchestrator.approval_manager.create(
            action="autoedit",
            command="autoedit change flow",
            risk_level=RiskLevel.WORKSPACE_WRITE,
            reason="Applying edits mutates workspace files.",
        )

        async def selector(title: str, text: str, options):
            return "dismiss"

        repl = Repl(orchestrator=orchestrator, console=Console(record=True), modal_selector=selector)

        asyncio.run(repl._resolve_interaction_gate())

        self.assertEqual(orchestrator.calls, ["/dismiss latest"])
        self.assertIsNone(orchestrator.approval_manager.latest())
