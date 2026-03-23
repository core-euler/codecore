"""Session runtime primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from ..domain.enums import TaskTag
from ..domain.models import ChatRequest, ProviderRoute


@dataclass(slots=True)
class SessionRuntime:
    session_id: str
    started_at: datetime
    task_tag: TaskTag = TaskTag.GENERAL
    active_files: list[str] = field(default_factory=list)
    active_skills: list[str] = field(default_factory=list)
    request_count: int = 0
    total_cost_usd: float = 0.0
    last_model_alias: str | None = None
    last_turn_id: str | None = None
    last_rating: int | None = None
    recent_tool_outputs: list[str] = field(default_factory=list)
    last_verification_summary: str | None = None
    last_failed_action: str | None = None
    last_failed_command: str | None = None
    last_failed_summary: str | None = None
    recent_patches: list[tuple[str, str | None]] = field(default_factory=list)
    last_context_file_count: int = 0
    last_context_token_count: int = 0
    allowed_action_types: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TurnContext:
    turn_id: str
    prompt: str
    created_at: datetime
    request: ChatRequest | None = None
    route: ProviderRoute | None = None
    response_text: str | None = None


def new_turn_context(prompt: str) -> TurnContext:
    return TurnContext(turn_id=str(uuid4()), prompt=prompt, created_at=datetime.now(timezone.utc))


def new_session_runtime() -> SessionRuntime:
    return SessionRuntime(session_id=str(uuid4()), started_at=datetime.now(timezone.utc))
