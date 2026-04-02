"""Baseline MCP registry control plane."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yaml

from ..domain.enums import HealthState
from ..mcp.manifests import MCPRegistryManifest, MCPServerManifest

_PRESET_SERVERS: dict[str, dict[str, object]] = {
    "filesystem": {
        "server_id": "filesystem",
        "enabled": True,
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
        "trust_level": "project",
        "risk_class": "readwrite",
    },
    "git": {
        "server_id": "git",
        "enabled": True,
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-git"],
        "trust_level": "project",
        "risk_class": "readonly",
    },
}


@dataclass(slots=True, frozen=True)
class MCPServerStatus:
    server_id: str
    enabled: bool
    state: HealthState
    detail: str
    transport: str
    command: str | None = None
    url: str | None = None
    risk_class: str | None = None
    trust_level: str | None = None


class MCPControlPlane:
    def __init__(self, registry_path: Path, registry: MCPRegistryManifest) -> None:
        self._registry_path = registry_path
        self._registry = registry

    def list_servers(self) -> tuple[MCPServerManifest, ...]:
        return tuple(self._registry.servers)

    def status(self) -> tuple[MCPServerStatus, ...]:
        return tuple(self._server_status(item) for item in self._registry.servers)

    def add_server(self, server_id: str, *, command_parts: tuple[str, ...] = (), url: str | None = None) -> MCPServerManifest:
        normalized = server_id.strip().lower()
        if not normalized:
            raise ValueError("Server id is required.")
        if any(item.server_id == normalized for item in self._registry.servers):
            raise ValueError(f"MCP server already exists: {normalized}")

        if url:
            server = MCPServerManifest(server_id=normalized, enabled=True, transport="http", url=url)
        elif not command_parts and normalized in _PRESET_SERVERS:
            server = MCPServerManifest.model_validate(_PRESET_SERVERS[normalized])
        elif command_parts:
            server = MCPServerManifest(
                server_id=normalized,
                enabled=True,
                transport="stdio",
                command=command_parts[0],
                args=list(command_parts[1:]),
            )
        else:
            presets = ", ".join(sorted(_PRESET_SERVERS))
            raise ValueError(f"Unknown MCP preset: {normalized}. Known presets: {presets}")

        self._registry = MCPRegistryManifest(servers=[*self._registry.servers, server])
        self._save()
        return server

    def disable_server(self, server_id: str) -> MCPServerManifest:
        return self._set_enabled(server_id, False)

    def enable_server(self, server_id: str) -> MCPServerManifest:
        return self._set_enabled(server_id, True)

    def _set_enabled(self, server_id: str, enabled: bool) -> MCPServerManifest:
        normalized = server_id.strip().lower()
        updated: list[MCPServerManifest] = []
        target: MCPServerManifest | None = None
        for item in self._registry.servers:
            if item.server_id != normalized:
                updated.append(item)
                continue
            target = item.model_copy(update={"enabled": enabled})
            updated.append(target)
        if target is None:
            raise KeyError(normalized)
        self._registry = MCPRegistryManifest(servers=updated)
        self._save()
        return target

    def _save(self) -> None:
        payload = {"servers": [item.model_dump(exclude_none=True) for item in self._registry.servers]}
        self._registry_path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")

    @staticmethod
    def _server_status(item: MCPServerManifest) -> MCPServerStatus:
        if not item.enabled:
            return MCPServerStatus(
                server_id=item.server_id,
                enabled=False,
                state=HealthState.UNKNOWN,
                detail="disabled",
                transport=item.transport,
                command=item.command,
                url=item.url,
                risk_class=item.risk_class,
                trust_level=item.trust_level,
            )
        if item.transport == "stdio":
            if not item.command:
                state = HealthState.UNAVAILABLE
                detail = "missing command"
            else:
                resolved = shutil.which(item.command)
                if resolved:
                    state = HealthState.HEALTHY
                    detail = resolved
                else:
                    state = HealthState.UNAVAILABLE
                    detail = f"command not found: {item.command}"
        elif item.transport in {"http", "https"}:
            parsed = urlparse(item.url or "")
            if parsed.scheme and parsed.netloc:
                state = HealthState.DEGRADED
                detail = "configured; runtime ping not implemented"
            else:
                state = HealthState.UNAVAILABLE
                detail = "invalid URL"
        else:
            state = HealthState.DEGRADED
            detail = f"unsupported transport health check: {item.transport}"
        return MCPServerStatus(
            server_id=item.server_id,
            enabled=item.enabled,
            state=state,
            detail=detail,
            transport=item.transport,
            command=item.command,
            url=item.url,
            risk_class=item.risk_class,
            trust_level=item.trust_level,
        )
