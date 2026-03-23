"""Resolve effective skills for a single prompt turn."""

from __future__ import annotations

from ..domain.enums import TaskTag
from ..domain.models import SkillDescriptor
from ..domain.contracts import SkillRegistry


class SkillResolver:
    def __init__(
        self,
        registry: SkillRegistry,
        *,
        defaults: tuple[str, ...] = (),
        auto_activate: bool = True,
    ) -> None:
        self._registry = registry
        self._defaults = defaults
        self._auto_activate = auto_activate

    async def resolve_for_turn(
        self,
        *,
        prompt: str,
        active_files: list[str],
        pinned_skills: list[str],
        task_tag: TaskTag,
    ) -> tuple[SkillDescriptor, ...]:
        all_skills = await self._registry.list_skills()
        skill_map = {skill.skill_id: skill for skill in all_skills}
        ordered_ids: list[str] = []

        for skill_id in (*self._defaults, *pinned_skills):
            if skill_id in skill_map and skill_id not in ordered_ids:
                ordered_ids.append(skill_id)

        if self._auto_activate:
            prompt_lower = prompt.lower()
            file_context = " ".join(active_files).lower()
            task_token = task_tag.value.lower()
            for skill in all_skills:
                if skill.skill_id in ordered_ids:
                    continue
                if self._matches(skill, prompt_lower=prompt_lower, file_context=file_context, task_token=task_token):
                    ordered_ids.append(skill.skill_id)

        return tuple(skill_map[skill_id] for skill_id in ordered_ids)

    def _matches(self, skill: SkillDescriptor, *, prompt_lower: str, file_context: str, task_token: str) -> bool:
        keywords = {skill.skill_id.lower(), *(tag.lower() for tag in skill.tags), *(trigger.lower() for trigger in skill.triggers)}
        for keyword in keywords:
            if not keyword:
                continue
            if keyword in prompt_lower or keyword in file_context or keyword == task_token:
                return True
        return False
