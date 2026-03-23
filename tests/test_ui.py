from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from prompt_toolkit.document import Document

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codecore.ui.repl import SlashCommandCompleter


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
