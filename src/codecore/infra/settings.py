"""Settings and path discovery."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .scaffold import ensure_project_scaffold


@dataclass(slots=True, frozen=True)
class Settings:
    project_root: Path
    config_dir: Path
    codex_home: Path
    project_config_path: Path
    skills_dir: Path
    legacy_skills_dir: Path
    provider_registry_path: Path
    mcp_registry_path: Path
    telemetry_db_path: Path
    repl_history_path: Path
    event_log_dir: Path
    artifact_dir: Path


def load_settings() -> Settings:
    project_root = Path.cwd().resolve()
    scaffold = ensure_project_scaffold(project_root)
    codex_home = project_root / ".codecore-home"
    project_config_path = scaffold.project_manifest_path
    skills_dir = scaffold.skills_dir
    provider_registry_path = scaffold.provider_registry_path
    mcp_registry_path = scaffold.mcp_registry_path
    telemetry_db_path = codex_home / "registry.db"
    repl_history_path = codex_home / "history.txt"
    event_log_dir = codex_home / "events"
    artifact_dir = codex_home / "artifacts"
    return Settings(
        project_root=project_root,
        config_dir=scaffold.config_dir,
        codex_home=codex_home,
        project_config_path=project_config_path,
        skills_dir=skills_dir,
        legacy_skills_dir=scaffold.legacy_skills_dir,
        provider_registry_path=provider_registry_path,
        mcp_registry_path=mcp_registry_path,
        telemetry_db_path=telemetry_db_path,
        repl_history_path=repl_history_path,
        event_log_dir=event_log_dir,
        artifact_dir=artifact_dir,
    )
