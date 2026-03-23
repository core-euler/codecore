"""Helpers for loading and validating CodeCore manifests."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from ..mcp.manifests import MCPRegistryManifest
from ..providers.manifests import ProviderRegistryManifest
from ..skills.manifests import SkillManifest
from .project_manifest import ProjectManifest

ModelT = TypeVar("ModelT", bound=BaseModel)


class ManifestError(ValueError):
    """Raised when a manifest is malformed or invalid."""


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ManifestError(f"Manifest does not exist: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ManifestError(f"Manifest root must be a mapping: {path}")
    return raw


def _validate(model_type: type[ModelT], raw: dict[str, Any], *, source: Path | str) -> ModelT:
    try:
        return model_type.model_validate(raw)
    except ValidationError as exc:
        raise ManifestError(f"Invalid manifest {source}: {exc}") from exc


def load_project_manifest(path: Path) -> ProjectManifest:
    return _validate(ProjectManifest, _read_yaml(path), source=path)


def load_provider_registry(path: Path) -> ProviderRegistryManifest:
    return _validate(ProviderRegistryManifest, _read_yaml(path), source=path)


def load_mcp_registry(path: Path) -> MCPRegistryManifest:
    return _validate(MCPRegistryManifest, _read_yaml(path), source=path)


def parse_skill_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    if not path.exists():
        raise ManifestError(f"Skill file does not exist: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ManifestError(f"Skill file is missing YAML frontmatter: {path}")
    _, _, rest = text.partition("---\n")
    frontmatter, separator, body = rest.partition("\n---\n")
    if not separator:
        raise ManifestError(f"Skill file is missing frontmatter terminator: {path}")
    raw = yaml.safe_load(frontmatter) or {}
    if not isinstance(raw, dict):
        raise ManifestError(f"Skill frontmatter must be a mapping: {path}")
    return raw, body.strip()


def load_skill_manifest(path: Path) -> SkillManifest:
    raw, _ = parse_skill_frontmatter(path)
    return _validate(SkillManifest, raw, source=path)
