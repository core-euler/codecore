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
from codecore.context.selectors import ContextSelector
from codecore.domain.enums import TaskTag
from codecore.domain.models import ChatMessage, ChatRequest
from codecore.infra.project_manifest import ProjectContextConfig, ProjectManifest, ProjectSkillsConfig
from codecore.kernel.runtime_state import RuntimeState
from codecore.kernel.session import new_session_runtime
from codecore.skills.loader import SkillLoader
from codecore.skills.registry import LocalSkillRegistry
from codecore.skills.resolver import SkillResolver


class ContextRuntimeTest(unittest.TestCase):
    def test_selector_respects_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sample = temp_path / "notes.txt"
            sample.write_text("\n".join(f"line {index}" for index in range(1, 80)), encoding="utf-8")
            manager = ContextManager(temp_path, max_file_bytes=100000)
            selector = ContextSelector(manager)
            active_files: list[str] = []
            manager.add_files(active_files, ["notes.txt"])

            selection = selector.select(active_files, budget_tokens=140, prompt="notes", task_tag=TaskTag.GENERAL)

            self.assertGreaterEqual(len(selection.chunks), 1)
            self.assertLessEqual(selection.total_tokens, 140)
            self.assertIn("FILE: notes.txt", selector.render(selection.chunks))

    def test_selector_uses_summary_first_for_large_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sample = temp_path / "big_module.py"
            sample.write_text("\n".join(f"def feature_{i}(): return {i}" for i in range(1, 300)), encoding="utf-8")
            manager = ContextManager(temp_path, max_file_bytes=400, summary_trigger_tokens=200)
            selector = ContextSelector(manager)
            active_files: list[str] = []
            manager.add_files(active_files, ["big_module.py"])

            selection = selector.select(active_files, budget_tokens=260, prompt="feature_12", task_tag=TaskTag.CODE)

            self.assertGreaterEqual(len(selection.chunks), 1)
            self.assertEqual(selection.files[0].strategy, "summary")
            self.assertEqual(selection.chunks[0].kind, "summary")
            self.assertIn("FILE SUMMARY: big_module.py", selector.render(selection.chunks))

    def test_selector_ranks_more_relevant_file_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "telegram_handlers.py").write_text("def on_update():\n    pass\n", encoding="utf-8")
            (temp_path / "billing_backend.py").write_text("def charge_invoice():\n    pass\n", encoding="utf-8")
            manager = ContextManager(temp_path, max_file_bytes=100000)
            selector = ContextSelector(manager)
            active_files: list[str] = []
            manager.add_files(active_files, ["billing_backend.py", "telegram_handlers.py"])

            selection = selector.select(active_files, budget_tokens=80, prompt="telegram update handling", task_tag=TaskTag.GENERAL)

            self.assertGreaterEqual(len(selection.files), 1)
            self.assertEqual(selection.files[0].path, "telegram_handlers.py")

    def test_composer_injects_skill_and_file_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            sample = temp_path / "architecture.md"
            sample.write_text("service boundary\nmodule split\ntradeoffs\n", encoding="utf-8")
            manager = ContextManager(temp_path, max_file_bytes=100000)
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            manager.add_files(session.active_files, ["architecture.md"])

            registry = LocalSkillRegistry.from_loader(SkillLoader((ROOT / "skills",)))
            resolver = SkillResolver(registry, defaults=(), auto_activate=True)
            manifest = ProjectManifest(
                project_id="context-test",
                default_task_tag="general",
                context=ProjectContextConfig(max_prompt_tokens=4096, auto_compact_threshold_pct=80),
                skills=ProjectSkillsConfig(auto_activate=True, defaults=[]),
            )
            composer = DefaultContextComposer(
                manager,
                session,
                runtime_state,
                manifest,
                skill_resolver=resolver,
            )

            request = ChatRequest(
                messages=(ChatMessage(role="user", content="Need architecture review of module boundaries"),),
                task_tag=TaskTag.ARCH,
            )
            composed = asyncio.run(composer.compose(request))

            self.assertIn("Active skills:", composed.system_prompt)
            self.assertIn("Skill: arch", composed.system_prompt)
            self.assertIn("Reference excerpt: boundaries.md", composed.system_prompt)
            self.assertIn("FILE: architecture.md", composed.system_prompt)
            self.assertIn("arch", composed.metadata["active_skills"])
            self.assertEqual(composed.metadata["selected_context_reports"][0]["path"], "architecture.md")

    def test_composer_injects_repo_map_when_no_files_selected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "src").mkdir()
            (temp_path / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
            manager = ContextManager(temp_path, max_file_bytes=100000)
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            manifest = ProjectManifest(
                project_id="repo-map-test",
                default_task_tag="general",
                context=ProjectContextConfig(max_prompt_tokens=4096, auto_compact_threshold_pct=80),
                skills=ProjectSkillsConfig(auto_activate=False, defaults=[]),
            )
            composer = DefaultContextComposer(manager, session, runtime_state, manifest)

            request = ChatRequest(messages=(ChatMessage(role="user", content="inspect repository layout"),))
            composed = asyncio.run(composer.compose(request))

            self.assertIn("Project repo map:", composed.system_prompt)
            self.assertIn("src/", composed.system_prompt)
            self.assertTrue(composed.metadata["repo_map_included"])


if __name__ == "__main__":
    unittest.main()
