"""Pydantic models for project-level configuration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProjectContextConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    max_prompt_tokens: int = Field(default=24000, ge=1024)
    auto_compact_threshold_pct: int = Field(default=80, ge=1, le=100)


class ProjectSkillsConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    auto_activate: bool = True
    defaults: list[str] = Field(default_factory=list)


class ProjectProvidersConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    preferred_aliases: list[str] = Field(default_factory=list)
    allow_vpn_routes: bool = False


class ProjectPoliciesConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    approval_policy: str = "on-write"


class ProjectManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(default=1, ge=1)
    project_id: str = Field(pattern=r"^[a-z0-9-]+$")
    default_task_tag: str = "general"
    context: ProjectContextConfig = Field(default_factory=ProjectContextConfig)
    skills: ProjectSkillsConfig = Field(default_factory=ProjectSkillsConfig)
    providers: ProjectProvidersConfig = Field(default_factory=ProjectProvidersConfig)
    policies: ProjectPoliciesConfig = Field(default_factory=ProjectPoliciesConfig)
