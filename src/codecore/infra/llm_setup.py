"""Persisted LLM setup and first-run onboarding helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..domain.enums import HealthState
from ..kernel.runtime_state import RuntimeState
from ..providers.health import ProviderHealthService
from ..providers.registry import ProviderRegistry
from .project_manifest import ProjectManifest
from .settings import Settings


@dataclass(slots=True, frozen=True)
class LLMSetupChoice:
    alias: str
    provider_id: str
    model_id: str
    env_name: str

    @property
    def label(self) -> str:
        return f"{self.alias} ({self.provider_id})"


def load_auth_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def persist_auth_env_var(path: Path, key: str, value: str) -> None:
    existing: dict[str, str] = {}
    if path.exists():
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            current_key, current_value = line.split("=", 1)
            existing[current_key.strip()] = current_value.strip().strip("'").strip('"')
    existing[key] = value
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# CodeCore persisted auth variables"]
    lines.extend(f"{name}={existing[name]}" for name in sorted(existing))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_default_model_alias(path: Path, alias: str) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(data, dict):
        data = {}
    providers = data.setdefault("providers", {})
    if not isinstance(providers, dict):
        providers = {}
        data["providers"] = providers
    current = providers.get("preferred_aliases") or []
    if not isinstance(current, list):
        current = []
    providers["preferred_aliases"] = [alias, *[item for item in current if item != alias]]
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


@dataclass(slots=True)
class LLMSetupService:
    settings: Settings
    project_manifest: ProjectManifest
    registry: ProviderRegistry
    health_service: ProviderHealthService
    runtime_state: RuntimeState

    def setup_choices(self) -> tuple[LLMSetupChoice, ...]:
        choices: list[LLMSetupChoice] = []
        for route in self.registry.list_routes():
            auth = route.auth_strategy or ""
            if not auth.startswith("env:"):
                continue
            env_name = auth.removeprefix("env:")
            alias = route.alias or route.model_id
            choices.append(
                LLMSetupChoice(
                    alias=alias,
                    provider_id=route.provider_id,
                    model_id=route.model_id,
                    env_name=env_name,
                )
            )
        return tuple(choices)

    async def is_ready(self) -> bool:
        snapshot = await self.health_service.refresh(force=True)
        return any(status.state in {HealthState.HEALTHY, HealthState.DEGRADED} for status in snapshot.values())

    def preferred_alias(self) -> str | None:
        if self.runtime_state.manual_model_alias:
            return self.runtime_state.manual_model_alias
        if self.project_manifest.providers.preferred_aliases:
            return self.project_manifest.providers.preferred_aliases[0]
        choices = self.setup_choices()
        return choices[0].alias if choices else None

    def resolve_choice(self, alias: str) -> LLMSetupChoice | None:
        normalized = alias.strip()
        for choice in self.setup_choices():
            if choice.alias == normalized or choice.model_id == normalized:
                return choice
        return None

    def save(self, *, alias: str, api_key: str) -> LLMSetupChoice:
        choice = self.resolve_choice(alias)
        if choice is None:
            raise ValueError(f"Unknown model alias: {alias}")
        token = api_key.strip()
        if not token:
            raise ValueError("API key cannot be empty.")
        os.environ[choice.env_name] = token
        persist_auth_env_var(self.settings.auth_env_path, choice.env_name, token)
        set_default_model_alias(self.settings.project_config_path, choice.alias)
        updated = [choice.alias, *[item for item in self.project_manifest.providers.preferred_aliases if item != choice.alias]]
        self.project_manifest.providers.preferred_aliases = updated
        self.runtime_state.manual_model_alias = choice.alias
        return choice
