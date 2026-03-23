"""Runtime registry for loaded skills."""

from __future__ import annotations

from ..domain.models import SkillDescriptor
from .loader import SkillLoader


class SkillNotFoundError(KeyError):
    """Raised when a skill is not registered."""


class LocalSkillRegistry:
    def __init__(self, skills: tuple[SkillDescriptor, ...]) -> None:
        self._skills = {skill.skill_id: skill for skill in skills}

    @classmethod
    def from_loader(cls, loader: SkillLoader) -> "LocalSkillRegistry":
        return cls(loader.load_all())

    async def list_skills(self) -> tuple[SkillDescriptor, ...]:
        return tuple(self._skills[skill_id] for skill_id in sorted(self._skills))

    async def resolve(self, skill_id: str) -> SkillDescriptor:
        try:
            return self._skills[skill_id]
        except KeyError as exc:
            raise SkillNotFoundError(skill_id) from exc

    def has_skill(self, skill_id: str) -> bool:
        return skill_id in self._skills
