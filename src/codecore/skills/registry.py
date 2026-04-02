"""Runtime registry for loaded skills."""

from __future__ import annotations

from ..domain.models import SkillDescriptor
from .loader import SkillLoader


class SkillNotFoundError(KeyError):
    """Raised when a skill is not registered."""


class LocalSkillRegistry:
    def __init__(self, skills: tuple[SkillDescriptor, ...], *, loader: SkillLoader | None = None) -> None:
        self._skills = {skill.skill_id: skill for skill in skills}
        self._loader = loader

    @classmethod
    def from_loader(cls, loader: SkillLoader) -> "LocalSkillRegistry":
        return cls(loader.load_all(), loader=loader)

    async def list_skills(self) -> tuple[SkillDescriptor, ...]:
        return tuple(self._skills[skill_id] for skill_id in sorted(self._skills))

    async def resolve(self, skill_id: str) -> SkillDescriptor:
        try:
            return self._skills[skill_id]
        except KeyError as exc:
            raise SkillNotFoundError(skill_id) from exc

    def has_skill(self, skill_id: str) -> bool:
        return skill_id in self._skills

    def skill_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._skills))

    def source_path(self, skill_id: str) -> str | None:
        skill = self._skills.get(skill_id)
        return skill.source_path if skill is not None else None

    def roots(self) -> tuple[str, ...]:
        if self._loader is None:
            return ()
        return tuple(str(root) for root in self._loader.roots)

    def reload(self) -> tuple[SkillDescriptor, ...]:
        if self._loader is None:
            return tuple(self._skills[skill_id] for skill_id in sorted(self._skills))
        skills = self._loader.load_all()
        self._skills = {skill.skill_id: skill for skill in skills}
        return tuple(self._skills[skill_id] for skill_id in sorted(self._skills))
