"""Pydantic models for MCP server manifests."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MCPServerManifest(BaseModel):
    model_config = ConfigDict(extra="allow")

    server_id: str = Field(pattern=r"^[a-z0-9-]+$")
    transport: str
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None
    auth_mode: str | None = None
    risk_class: str | None = None
    trust_level: str | None = None
    data_sensitivity: str | None = None


class MCPRegistryManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    servers: list[MCPServerManifest]
