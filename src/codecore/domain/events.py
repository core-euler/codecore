"""Event envelope definitions for runtime event sourcing."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .enums import EventKind, TaskTag


@dataclass(slots=True, frozen=True)
class EventEnvelope:
    event_id: str
    kind: EventKind
    timestamp: datetime
    session_id: str
    turn_id: str | None = None
    project_id: str | None = None
    task_tag: TaskTag | None = None
    provider_id: str | None = None
    model_id: str | None = None
    pipeline_id: str | None = None
    skill_ids: tuple[str, ...] = ()
    mcp_server_ids: tuple[str, ...] = ()
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        kind: EventKind,
        session_id: str,
        turn_id: str | None = None,
        project_id: str | None = None,
        task_tag: TaskTag | None = None,
        provider_id: str | None = None,
        model_id: str | None = None,
        pipeline_id: str | None = None,
        skill_ids: tuple[str, ...] = (),
        mcp_server_ids: tuple[str, ...] = (),
        payload: dict[str, Any] | None = None,
    ) -> "EventEnvelope":
        return cls(
            event_id=str(uuid4()),
            kind=kind,
            timestamp=datetime.now(timezone.utc),
            session_id=session_id,
            turn_id=turn_id,
            project_id=project_id,
            task_tag=task_tag,
            provider_id=provider_id,
            model_id=model_id,
            pipeline_id=pipeline_id,
            skill_ids=skill_ids,
            mcp_server_ids=mcp_server_ids,
            payload=payload or {},
        )
