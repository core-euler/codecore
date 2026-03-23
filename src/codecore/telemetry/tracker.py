"""Telemetry sink backed by JSONL and SQLite."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from ..domain.contracts import TelemetrySink
from ..domain.enums import EventKind
from ..domain.events import EventEnvelope
from ..infra import sqlite as sqlite_helpers


class TelemetryTracker(TelemetrySink):
    def __init__(self, db_path: Path, event_dir: Path) -> None:
        event_dir.mkdir(parents=True, exist_ok=True)
        self._db = sqlite_helpers.connect(db_path)
        self._event_dir = event_dir

    async def publish(self, event: EventEnvelope) -> None:
        self._append_event(event)
        self._project(event)

    def _append_event(self, event: EventEnvelope) -> None:
        path = self._event_dir / f"{event.session_id}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(self._event_record(event), ensure_ascii=True) + "\n")

    def _event_record(self, event: EventEnvelope) -> dict:
        record = asdict(event) if is_dataclass(event) else dict(event)
        for key, value in list(record.items()):
            if isinstance(value, datetime):
                record[key] = value.isoformat()
            elif hasattr(value, "value"):
                record[key] = value.value
        return record

    def _project(self, event: EventEnvelope) -> None:
        if event.kind == EventKind.SESSION_STARTED:
            self._db.execute(
                "INSERT OR REPLACE INTO sessions (id, started_at, task_tag, provider, model, skill) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    event.session_id,
                    event.timestamp.isoformat(),
                    event.task_tag.value if event.task_tag else None,
                    event.provider_id,
                    event.model_id,
                    ",".join(event.skill_ids) if event.skill_ids else None,
                ),
            )
        elif event.kind == EventKind.SESSION_FINISHED:
            self._db.execute(
                "UPDATE sessions SET ended_at = ?, provider = COALESCE(?, provider), model = COALESCE(?, model) WHERE id = ?",
                (event.timestamp.isoformat(), event.provider_id, event.model_id, event.session_id),
            )
        elif event.kind == EventKind.SKILL_ACTIVATED:
            self._db.execute(
                "UPDATE sessions SET skill = ? WHERE id = ?",
                (
                    ",".join(event.skill_ids) if event.skill_ids else None,
                    event.session_id,
                ),
            )
        elif event.kind == EventKind.MODEL_INVOKED:
            payload = event.payload
            self._db.execute(
                "INSERT INTO requests (id, session_id, turn_id, timestamp, model, model_alias, provider, task_tag, skills, input_tokens, output_tokens, latency_ms, cost_usd, rating) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(uuid4()),
                    event.session_id,
                    event.turn_id,
                    event.timestamp.isoformat(),
                    event.model_id,
                    payload.get("model_alias"),
                    event.provider_id,
                    event.task_tag.value if event.task_tag else None,
                    ",".join(event.skill_ids) if event.skill_ids else None,
                    payload.get("input_tokens"),
                    payload.get("output_tokens"),
                    payload.get("latency_ms"),
                    payload.get("cost_usd"),
                    payload.get("rating"),
                ),
            )
        elif event.kind == EventKind.FEEDBACK_RECORDED:
            self._db.execute(
                "UPDATE requests SET rating = ? WHERE session_id = ? AND turn_id = ?",
                (event.payload.get("rating"), event.session_id, event.turn_id),
            )
        self._db.commit()
