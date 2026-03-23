from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codecore.domain.enums import TaskTag
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


if __name__ == "__main__":
    unittest.main()
