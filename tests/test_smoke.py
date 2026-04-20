from __future__ import annotations

import os
import subprocess
import sys
import tempfile
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
from codecore.infra.settings import load_settings
from codecore.ui.commands import COMMAND_SPECS


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

    def test_load_settings_bootstraps_scaffold_in_empty_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir).resolve()
            previous = Path.cwd()
            os.chdir(temp_path)
            try:
                settings = load_settings()
                self.assertEqual(settings.project_config_path, temp_path / ".codecore" / "project.yaml")
                self.assertTrue(settings.project_config_path.exists())
                self.assertTrue(settings.provider_registry_path.exists())
                self.assertTrue(settings.mcp_registry_path.exists())
                self.assertTrue(settings.skills_dir.exists())
                self.assertTrue((settings.skills_dir / "discover" / "SKILL.md").exists())
                self.assertTrue((settings.skills_dir / "implement" / "SKILL.md").exists())
            finally:
                os.chdir(previous)

    def test_command_specs_are_sorted_alphabetically(self) -> None:
        names = [spec.name for spec in COMMAND_SPECS]
        self.assertEqual(names, sorted(names))


class EntryPointSmokeTest(unittest.TestCase):
    def test_module_entrypoint_runs(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "codecore"],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(SRC), "DEEPSEEK_API_KEY": "test-key"},
            input="/exit\n",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("[codecore] scaffold booted", proc.stdout)
        self.assertIn("Session finished.", proc.stdout)

    def test_module_entrypoint_requires_llm_configuration_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            proc = subprocess.run(
                [sys.executable, "-m", "codecore"],
                cwd=temp_dir,
                env={
                    **os.environ,
                    "PYTHONPATH": str(SRC),
                    "DEEPSEEK_API_KEY": "",
                    "MISTRAL_API_KEY": "",
                    "OPENROUTER_API_KEY": "",
                },
                input="/exit\n",
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertIn("No LLM is configured", proc.stdout)


if __name__ == "__main__":
    unittest.main()
