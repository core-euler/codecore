from __future__ import annotations

import sys
import unittest
from pathlib import Path

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
