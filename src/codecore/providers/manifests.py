"""Pydantic models for provider manifests."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProviderModelManifest(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    alias: str | None = None
    max_context: int | None = Field(default=None, ge=1)
    supports_tools: bool = False
    supports_json: bool = False
    supports_vision: bool = False
    cost_per_1k_in: float | None = Field(default=None, ge=0)
    cost_per_1k_out: float | None = Field(default=None, ge=0)


class ProviderManifest(BaseModel):
    model_config = ConfigDict(extra="allow")

    provider_id: str = Field(pattern=r"^[a-z0-9-]+$")
    transport: str
    base_url: str | None = None
    auth_strategy: str | None = None
    priority: int = Field(default=100, ge=1)
    vpn_required: bool = False
    models: list[ProviderModelManifest]


class ProviderRegistryManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    providers: list[ProviderManifest]
