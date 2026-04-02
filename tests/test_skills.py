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

from codecore.domain.enums import TaskTag
from codecore.context.composer import DefaultContextComposer
from codecore.context.manager import ContextManager
from codecore.infra.manifest_loader import load_provider_registry
from codecore.infra.project_manifest import ProjectManifest
from codecore.kernel.event_bus import EventBus
from codecore.kernel.orchestrator import Orchestrator
from codecore.kernel.runtime_state import RuntimeState
from codecore.kernel.session import new_session_runtime
from codecore.providers.adapters.base import AdapterFactory
from codecore.providers.broker import PolicyDrivenBroker
from codecore.providers.health import ProviderHealthService
from codecore.providers.registry import ProviderRegistry
from codecore.skills.composer import SkillPromptComposer
from codecore.skills.loader import SkillLoader
from codecore.skills.registry import LocalSkillRegistry
from codecore.skills.resolver import SkillResolver


class SkillRuntimeTest(unittest.TestCase):
    def test_loader_discovers_builtin_skills(self) -> None:
        registry = LocalSkillRegistry.from_loader(SkillLoader((ROOT / "skills",)))

        async def run() -> tuple[str, ...]:
            skills = await registry.list_skills()
            return tuple(skill.skill_id for skill in skills)

        skill_ids = asyncio.run(run())
        self.assertEqual(skill_ids, ("arch", "backend", "review", "telegram"))

    def test_resolver_combines_auto_and_pinned_skills(self) -> None:
        registry = LocalSkillRegistry.from_loader(SkillLoader((ROOT / "skills",)))
        resolver = SkillResolver(registry, defaults=(), auto_activate=True)

        async def run() -> tuple[str, ...]:
            skills = await resolver.resolve_for_turn(
                prompt="Need architecture review for service boundaries",
                active_files=["docs/adr/0001-hexagonal-runtime.md"],
                pinned_skills=["review"],
                task_tag=TaskTag.ARCH,
            )
            return tuple(skill.skill_id for skill in skills)

        skill_ids = asyncio.run(run())
        self.assertIn("arch", skill_ids)
        self.assertIn("review", skill_ids)

    def test_prompt_composer_renders_skill_block(self) -> None:
        registry = LocalSkillRegistry.from_loader(SkillLoader((ROOT / "skills",)))

        async def run() -> str:
            skill = await registry.resolve("arch")
            text, _ = SkillPromptComposer().compose((skill,), budget_tokens=512, prompt="check module boundaries")
            return text

        text = asyncio.run(run())
        self.assertIn("Skill: arch", text)
        self.assertIn("Instructions:", text)
        self.assertIn("Reference excerpt: boundaries.md", text)

    def test_skill_command_can_create_project_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            skill_root = temp_path / ".codecore" / "skills"
            skill_root.mkdir(parents=True)
            registry = LocalSkillRegistry.from_loader(SkillLoader((skill_root,)))
            provider_registry = ProviderRegistry(load_provider_registry(ROOT / ".codecore" / "providers" / "registry.yaml"))
            health = ProviderHealthService(provider_registry, AdapterFactory())
            session = new_session_runtime()
            runtime_state = RuntimeState.default()
            context_manager = ContextManager(temp_path)
            orchestrator = Orchestrator(
                session=session,
                runtime_state=runtime_state,
                provider_registry=provider_registry,
                broker=PolicyDrivenBroker(provider_registry, health),
                health_service=health,
                adapter_factory=AdapterFactory(),
                context_manager=context_manager,
                context_composer=DefaultContextComposer(
                    context_manager,
                    session,
                    runtime_state,
                    ProjectManifest(project_id="skill-test"),
                ),
                event_bus=EventBus(sinks=[]),
                skill_registry=registry,
            )

            async def run():
                return await orchestrator.handle_line("/skill new discoverer")

            result = asyncio.run(run())

            self.assertIn(".codecore/skills/discoverer/SKILL.md", result.output)
            self.assertTrue((skill_root / "discoverer" / "SKILL.md").exists())
            self.assertIn("discoverer", registry.skill_ids())


if __name__ == "__main__":
    unittest.main()
