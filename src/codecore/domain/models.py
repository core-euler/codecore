"""Domain models used by ports and runtime state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .enums import HealthState, MemoryScope, RuntimeMode, TaskTag


@dataclass(slots=True, frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(slots=True, frozen=True)
class ChatRequest:
    messages: tuple[ChatMessage, ...]
    system_prompt: str = ""
    task_tag: TaskTag = TaskTag.GENERAL
    model_hint: str | None = None
    max_output_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ChatResult:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    cost_usd: float | None = None
    finish_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class ModelCapabilities:
    supports_streaming: bool = True
    supports_tools: bool = False
    supports_json: bool = False
    supports_vision: bool = False
    max_context_tokens: int | None = None


@dataclass(slots=True, frozen=True)
class HealthStatus:
    state: HealthState
    checked_at: datetime
    latency_ms: int | None = None
    detail: str = ""

    @classmethod
    def unknown(cls) -> "HealthStatus":
        return cls(state=HealthState.UNKNOWN, checked_at=datetime.now(timezone.utc))


@dataclass(slots=True, frozen=True)
class ProviderRoute:
    provider_id: str
    model_id: str
    alias: str | None = None
    priority: int = 100
    vpn_required: bool = False
    cost_hint_in: float | None = None
    cost_hint_out: float | None = None
    transport: str | None = None
    base_url: str | None = None
    auth_strategy: str | None = None
    supports_tools: bool = False
    supports_json: bool = False
    supports_vision: bool = False
    max_context_tokens: int | None = None


@dataclass(slots=True, frozen=True)
class SkillDescriptor:
    skill_id: str
    description: str
    version: str = "1"
    summary: str | None = None
    tags: tuple[str, ...] = ()
    triggers: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()
    instructions: str = ""
    source_path: str | None = None
    reference_paths: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class ArtifactRef:
    artifact_id: str
    kind: str
    path: str
    summary: str = ""


@dataclass(slots=True, frozen=True)
class MemoryRecord:
    memory_id: str
    scope: MemoryScope
    kind: str
    summary: str
    content: str
    tags: tuple[str, ...] = ()
    session_id: str | None = None
    turn_id: str | None = None
    task_tag: TaskTag | None = None
    provider_id: str | None = None
    model_id: str | None = None
    skill_ids: tuple[str, ...] = ()
    quality_score: float = 0.0
    rating: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProjectContext:
    project_root: str
    active_files: list[str] = field(default_factory=list)
    active_skills: list[str] = field(default_factory=list)
    mode: RuntimeMode = RuntimeMode.INTERACTIVE
