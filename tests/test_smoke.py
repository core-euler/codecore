from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codecore.app import create_app
from codecore.bootstrap import bootstrap_application
from codecore.domain.events import EventEnvelope
from codecore.domain.enums import EventKind


class BootstrapSmokeTest(unittest.TestCase):
    def test_bootstrap_builds_context(self) -> None:
        context = bootstrap_application()
        self.assertEqual(context.settings.project_root, ROOT)
        self.assertTrue(context.session.session_id)
        self.assertIn("scaffold booted", context.startup_summary())

    def test_event_factory_builds_envelope(self) -> None:
        event = EventEnvelope.create(kind=EventKind.SESSION_STARTED, session_id="session-1")
        self.assertEqual(event.kind, EventKind.SESSION_STARTED)
        self.assertEqual(event.session_id, "session-1")
        self.assertTrue(event.event_id)

    def test_app_factory_returns_app(self) -> None:
        app = create_app()
        self.assertEqual(app.bootstrap.project_manifest.project_id, "codecore")


class EntryPointSmokeTest(unittest.TestCase):
    def test_module_entrypoint_runs(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "codecore"],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(SRC)},
            input="/exit\n",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("[codecore] scaffold booted", proc.stdout)
        self.assertIn("Session finished.", proc.stdout)

    def test_module_prompt_preserves_square_brackets_in_output(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "codecore"],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(SRC)},
            input="hello\n/exit\n",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("[mock:mock] hello", proc.stdout)


if __name__ == "__main__":
    unittest.main()
