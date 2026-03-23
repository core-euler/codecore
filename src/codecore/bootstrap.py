"""Bootstrap composition root for CodeCore."""

from __future__ import annotations

from dataclasses import dataclass

from .domain.enums import TaskTag
from .infra.settings import Settings, load_settings
from .infra.manifest_loader import load_mcp_registry, load_project_manifest, load_provider_registry
from .infra.project_manifest import ProjectManifest
from .kernel.runtime_state import RuntimeState
from .kernel.session import SessionRuntime, new_session_runtime
from .mcp.manifests import MCPRegistryManifest
from .providers.manifests import ProviderRegistryManifest


@dataclass(slots=True)
class BootstrapContext:
    settings: Settings
    project_manifest: ProjectManifest
    provider_registry: ProviderRegistryManifest
    mcp_registry: MCPRegistryManifest
    runtime_state: RuntimeState
    session: SessionRuntime

    def startup_summary(self) -> str:
        return (
            "[codecore] scaffold booted"
            f" | project={self.settings.project_root.name}"
            f" | config={self.project_manifest.project_id}"
            f" | providers={len(self.provider_registry.providers)}"
            f" | mcp={len(self.mcp_registry.servers)}"
            f" | session={self.session.session_id}"
        )


def bootstrap_application() -> BootstrapContext:
    settings = load_settings()
    project_manifest = load_project_manifest(settings.project_config_path)
    provider_registry = load_provider_registry(settings.provider_registry_path)
    mcp_registry = load_mcp_registry(settings.mcp_registry_path)
    runtime_state = RuntimeState.default()
    session = new_session_runtime()
    try:
        session.task_tag = TaskTag(project_manifest.default_task_tag)
    except ValueError:
        session.task_tag = TaskTag.GENERAL
    return BootstrapContext(
        settings=settings,
        project_manifest=project_manifest,
        provider_registry=provider_registry,
        mcp_registry=mcp_registry,
        runtime_state=runtime_state,
        session=session,
    )
