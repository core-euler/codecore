"""Load project skills from SKILL.md files."""

from __future__ import annotations

from pathlib import Path

from ..domain.models import SkillDescriptor
from ..infra.manifest_loader import parse_skill_frontmatter
from .manifests import SkillManifest


class SkillLoader:
    def __init__(self, roots: tuple[Path, ...]) -> None:
        self._roots = roots

    def discover_files(self) -> tuple[Path, ...]:
        files: list[Path] = []
        seen: set[Path] = set()
        for root in self._roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("SKILL.md")):
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                files.append(resolved)
        return tuple(files)

    def load_file(self, path: Path) -> SkillDescriptor:
        raw, body = parse_skill_frontmatter(path)
        manifest = SkillManifest.model_validate(raw)
        return SkillDescriptor(
            skill_id=manifest.name,
            description=manifest.description,
            version=manifest.version,
            summary=manifest.summary,
            tags=tuple(manifest.tags),
            triggers=tuple(manifest.triggers),
            constraints=tuple(manifest.constraints),
            stop_conditions=tuple(manifest.stop_conditions),
            instructions=body,
            source_path=str(path),
            reference_paths=tuple(str(reference) for reference in self._discover_references(path.parent)),
        )

    def load_all(self) -> tuple[SkillDescriptor, ...]:
        loaded = [self.load_file(path) for path in self.discover_files()]
        by_id: dict[str, SkillDescriptor] = {}
        for skill in loaded:
            if skill.skill_id in by_id:
                raise ValueError(f"Duplicate skill id detected: {skill.skill_id}")
            by_id[skill.skill_id] = skill
        return tuple(by_id[skill_id] for skill_id in sorted(by_id))

    def _discover_references(self, skill_dir: Path) -> tuple[Path, ...]:
        reference_dir = skill_dir / "references"
        if not reference_dir.exists():
            return ()
        return tuple(path.resolve() for path in sorted(reference_dir.glob("*.md")) if path.is_file())
