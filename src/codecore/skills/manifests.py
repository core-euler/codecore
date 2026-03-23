"""Pydantic models for skill manifests."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SkillManifest(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(pattern=r"^[a-z0-9-]+$")
    description: str = Field(min_length=1)
    version: str = "1"
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    stop_conditions: list[str] = Field(default_factory=list)
