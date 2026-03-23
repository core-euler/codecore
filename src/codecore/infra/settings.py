"""Settings and path discovery."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class Settings:
    project_root: Path
    codex_home: Path
    project_config_path: Path
    skills_dir: Path
    provider_registry_path: Path
    mcp_registry_path: Path
    telemetry_db_path: Path
    repl_history_path: Path
    event_log_dir: Path
    artifact_dir: Path


def load_settings() -> Settings:
    project_root = Path.cwd().resolve()
    codex_home = project_root / ".codecore-home"
    project_config_path = project_root / ".codecore" / "project.yaml"
    skills_dir = project_root / "skills"
    provider_registry_path = project_root / "providers" / "registry.yaml"
    mcp_registry_path = project_root / "mcp" / "servers.yaml"
    telemetry_db_path = codex_home / "registry.db"
    repl_history_path = codex_home / "history.txt"
    event_log_dir = codex_home / "events"
    artifact_dir = codex_home / "artifacts"
    return Settings(
        project_root=project_root,
        codex_home=codex_home,
        project_config_path=project_config_path,
        skills_dir=skills_dir,
        provider_registry_path=provider_registry_path,
        mcp_registry_path=mcp_registry_path,
        telemetry_db_path=telemetry_db_path,
        repl_history_path=repl_history_path,
        event_log_dir=event_log_dir,
        artifact_dir=artifact_dir,
    )
