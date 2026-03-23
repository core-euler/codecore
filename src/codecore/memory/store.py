"""SQLite-backed memory store with simple lexical recall."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ..domain.contracts import MemoryStore, TelemetrySink
from ..domain.enums import EventKind, MemoryScope, TaskTag
from ..domain.events import EventEnvelope
from ..domain.models import MemoryRecord
from ..infra import sqlite as sqlite_helpers
from .taxonomy import build_turn_memory, normalize_terms, rating_to_quality

_MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
  id TEXT PRIMARY KEY,
  session_id TEXT,
  turn_id TEXT,
  created_at TEXT NOT NULL,
  scope TEXT NOT NULL,
  kind TEXT NOT NULL,
  summary TEXT NOT NULL,
  content TEXT NOT NULL,
  task_tag TEXT,
  provider TEXT,
  model TEXT,
  skills TEXT,
  tags TEXT,
  quality_score REAL DEFAULT 0,
  rating INTEGER,
  metadata_json TEXT,
  source_event_id TEXT,
  UNIQUE(session_id, turn_id, kind)
);

CREATE INDEX IF NOT EXISTS idx_memories_turn ON memories(session_id, turn_id);
CREATE INDEX IF NOT EXISTS idx_memories_task_tag ON memories(task_tag);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at DESC);
"""


@dataclass(slots=True, frozen=True)
class MemoryWritePolicy:
    min_prompt_chars: int = 16
    min_response_chars: int = 32

    def should_persist(
        self,
        *,
        prompt: str,
        response_text: str,
        task_tag: TaskTag | None,
        skill_ids: tuple[str, ...],
        active_files: tuple[str, ...],
    ) -> bool:
        if not prompt or not response_text:
            return False
        if task_tag is not None and task_tag != TaskTag.GENERAL:
            return True
        if skill_ids or active_files:
            return True
        if len(prompt.strip()) >= self.min_prompt_chars and len(response_text.strip()) >= self.min_response_chars:
            return True
        return False


class SQLiteMemoryStore(MemoryStore, TelemetrySink):
    def __init__(self, db_path: Path, *, write_policy: MemoryWritePolicy | None = None) -> None:
        self._db = sqlite_helpers.connect(db_path)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(_MEMORY_SCHEMA)
        self._write_policy = write_policy or MemoryWritePolicy()
        self._db.commit()

    async def publish(self, event: EventEnvelope) -> None:
        if event.kind == EventKind.MODEL_INVOKED:
            payload = event.payload
            prompt = str(payload.get("prompt") or "").strip()
            response_text = str(payload.get("response_text") or payload.get("response_excerpt") or "").strip()
            if not prompt or not response_text:
                return
            task_tag = _coerce_task_tag(event.task_tag)
            active_files = tuple(payload.get("active_files") or ())
            skill_ids = tuple(event.skill_ids)
            if not self._write_policy.should_persist(
                prompt=prompt,
                response_text=response_text,
                task_tag=task_tag,
                skill_ids=skill_ids,
                active_files=active_files,
            ):
                return
            record = build_turn_memory(
                session_id=event.session_id,
                turn_id=event.turn_id or event.event_id,
                prompt=prompt,
                response_text=response_text,
                task_tag=task_tag,
                provider_id=event.provider_id,
                model_id=event.model_id,
                skill_ids=skill_ids,
                active_files=active_files,
            )
            await self.write(record)
            self._db.execute(
                "UPDATE memories SET source_event_id = ? WHERE session_id = ? AND turn_id = ? AND kind = ?",
                (event.event_id, record.session_id, record.turn_id, record.kind),
            )
            self._db.commit()
            return
        if event.kind == EventKind.FEEDBACK_RECORDED and event.turn_id:
            rating = event.payload.get("rating")
            quality = rating_to_quality(rating if isinstance(rating, int) else None)
            self._db.execute(
                "UPDATE memories SET rating = ?, quality_score = ? WHERE session_id = ? AND turn_id = ?",
                (rating, quality, event.session_id, event.turn_id),
            )
            if isinstance(rating, int) and rating >= 4:
                self._promote_success_memory(event.session_id, event.turn_id, rating)
            self._db.commit()
            return
        if event.kind == EventKind.SESSION_FINISHED:
            self._write_session_summary(event)
            self._db.commit()
            return
        if event.kind == EventKind.FALLBACK_TRIGGERED:
            self._write_governance_memory(event)
            self._db.commit()
            return

    async def write(self, record: MemoryRecord) -> None:
        self._db.execute(
            """
            INSERT INTO memories (
              id, session_id, turn_id, created_at, scope, kind, summary, content,
              task_tag, provider, model, skills, tags, quality_score, rating, metadata_json, source_event_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id, turn_id, kind) DO UPDATE SET
              summary = excluded.summary,
              content = excluded.content,
              task_tag = excluded.task_tag,
              provider = excluded.provider,
              model = excluded.model,
              skills = excluded.skills,
              tags = excluded.tags,
              quality_score = excluded.quality_score,
              rating = COALESCE(excluded.rating, memories.rating),
              metadata_json = excluded.metadata_json
            """,
            (
                record.memory_id,
                record.session_id,
                record.turn_id,
                record.created_at.isoformat(),
                record.scope.value,
                record.kind,
                record.summary,
                record.content,
                record.task_tag.value if record.task_tag else None,
                record.provider_id,
                record.model_id,
                ",".join(record.skill_ids) if record.skill_ids else None,
                ",".join(record.tags) if record.tags else None,
                record.quality_score,
                record.rating,
                sqlite_helpers.json_dumps(record.metadata),
                record.metadata.get("source_event_id"),
            ),
        )
        self._db.commit()

    async def recall(self, *, query: str, limit: int = 10) -> tuple[MemoryRecord, ...]:
        rows = self._db.execute(
            "SELECT * FROM memories ORDER BY created_at DESC LIMIT 250"
        ).fetchall()
        query_terms = set(normalize_terms(query))
        scored: list[tuple[float, MemoryRecord]] = []
        for row in rows:
            record = _row_to_record(row)
            haystack_terms = set(record.tags) | set(normalize_terms(record.summary, record.content))
            overlap = len(query_terms & haystack_terms)
            summary_bonus = 1.5 if query and query.lower() in record.summary.lower() else 0.0
            task_bonus = 0.75 if record.task_tag and record.task_tag.value in query.lower() else 0.0
            score = overlap * 2.0 + summary_bonus + task_bonus + record.quality_score * 3.0
            if score <= 0 and query_terms:
                continue
            scored.append((score, record))
        scored.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
        return tuple(record for _, record in scored[:limit])

    def stats(self) -> dict[str, float | int | None]:
        row = self._db.execute(
            "SELECT COUNT(*), AVG(rating), AVG(quality_score) FROM memories"
        ).fetchone()
        return {
            "count": row[0] or 0,
            "avg_rating": row[1],
            "avg_quality_score": row[2],
        }

    def list_recent(self, *, limit: int = 100) -> tuple[MemoryRecord, ...]:
        rows = self._db.execute(
            "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return tuple(_row_to_record(row) for row in rows)

    def close(self) -> None:
        self._db.close()

    def _promote_success_memory(self, session_id: str, turn_id: str, rating: int) -> None:
        row = self._db.execute(
            "SELECT * FROM memories WHERE session_id = ? AND turn_id = ? AND kind = 'turn.outcome' ORDER BY created_at DESC LIMIT 1",
            (session_id, turn_id),
        ).fetchone()
        if row is None:
            return
        source = _row_to_record(row)
        project_memory = MemoryRecord(
            memory_id=str(uuid4()),
            scope=MemoryScope.PROJECT,
            kind="project.preference",
            summary=(
                f"Successful {source.task_tag.value if source.task_tag else 'general'} flow with "
                f"{source.model_id or 'unknown-model'}"
            ),
            content=(
                f"source_summary: {source.summary}\n"
                f"provider: {source.provider_id or '<unknown>'}\n"
                f"model: {source.model_id or '<unknown>'}\n"
                f"skills: {', '.join(source.skill_ids) if source.skill_ids else '<none>'}\n"
                f"highlights: {', '.join(source.metadata.get('highlights', [])) or '<none>'}"
            ),
            tags=source.tags,
            session_id=session_id,
            turn_id=turn_id,
            task_tag=source.task_tag,
            provider_id=source.provider_id,
            model_id=source.model_id,
            skill_ids=source.skill_ids,
            quality_score=rating_to_quality(rating),
            rating=rating,
            created_at=datetime.now(timezone.utc),
            metadata={"source_scope": source.scope.value, "file_names": source.metadata.get("file_names", [])},
        )
        self._insert_memory(project_memory)
        if rating >= 5:
            global_memory = MemoryRecord(
                memory_id=str(uuid4()),
                scope=MemoryScope.GLOBAL,
                kind="global.practice",
                summary=project_memory.summary,
                content=project_memory.content,
                tags=project_memory.tags,
                session_id=session_id,
                turn_id=turn_id,
                task_tag=project_memory.task_tag,
                provider_id=project_memory.provider_id,
                model_id=project_memory.model_id,
                skill_ids=project_memory.skill_ids,
                quality_score=1.0,
                rating=rating,
                created_at=datetime.now(timezone.utc),
                metadata={"source_scope": project_memory.scope.value},
            )
            self._insert_memory(global_memory)

    def _write_session_summary(self, event: EventEnvelope) -> None:
        row = self._db.execute(
            """
            SELECT COUNT(*) AS requests,
                   AVG(rating) AS avg_rating,
                   SUM(cost_usd) AS total_cost_usd,
                   GROUP_CONCAT(DISTINCT COALESCE(model_alias, model)) AS models,
                   GROUP_CONCAT(DISTINCT provider) AS providers,
                   GROUP_CONCAT(DISTINCT skills) AS skills
            FROM requests
            WHERE session_id = ?
            """,
            (event.session_id,),
        ).fetchone()
        requests = row["requests"] or 0
        if not requests:
            return
        summary = (
            f"Session finished with {requests} requests; "
            f"models={row['models'] or '<unknown>'}; avg_rating={_format_optional(row['avg_rating'])}"
        )
        record = MemoryRecord(
            memory_id=str(uuid4()),
            scope=MemoryScope.SESSION,
            kind="session.summary",
            summary=summary,
            content=(
                f"providers: {row['providers'] or '<unknown>'}\n"
                f"models: {row['models'] or '<unknown>'}\n"
                f"skills: {row['skills'] or '<none>'}\n"
                f"total_cost_usd: {_format_optional(row['total_cost_usd'])}\n"
                f"avg_rating: {_format_optional(row['avg_rating'])}"
            ),
            session_id=event.session_id,
            task_tag=event.task_tag,
            provider_id=event.provider_id,
            model_id=event.model_id,
            skill_ids=tuple(event.skill_ids),
            quality_score=rating_to_quality(int(round(row["avg_rating"]))) if row["avg_rating"] is not None else 0.25,
            created_at=datetime.now(timezone.utc),
            metadata={"request_count": requests},
        )
        self._insert_memory(record)

    def _write_governance_memory(self, event: EventEnvelope) -> None:
        payload = event.payload
        next_alias = payload.get("next_alias") or payload.get("next_model_id") or "<none>"
        record = MemoryRecord(
            memory_id=str(uuid4()),
            scope=MemoryScope.GOVERNANCE,
            kind="governance.fallback",
            summary=f"Fallback from {payload.get('failed_alias') or event.model_id or '<unknown>'} to {next_alias}",
            content=(
                f"provider: {event.provider_id or '<unknown>'}\n"
                f"model: {event.model_id or '<unknown>'}\n"
                f"error: {payload.get('error') or '<none>'}\n"
                f"next_provider: {payload.get('next_provider_id') or '<unknown>'}\n"
                f"next_model: {payload.get('next_model_id') or '<unknown>'}"
            ),
            session_id=event.session_id,
            turn_id=event.turn_id,
            task_tag=event.task_tag,
            provider_id=event.provider_id,
            model_id=event.model_id,
            skill_ids=tuple(event.skill_ids),
            quality_score=0.4,
            created_at=datetime.now(timezone.utc),
            metadata=payload,
        )
        self._insert_memory(record)

    def _insert_memory(self, record: MemoryRecord) -> None:
        self._db.execute(
            """
            INSERT INTO memories (
              id, session_id, turn_id, created_at, scope, kind, summary, content,
              task_tag, provider, model, skills, tags, quality_score, rating, metadata_json, source_event_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id, turn_id, kind) DO UPDATE SET
              summary = excluded.summary,
              content = excluded.content,
              task_tag = excluded.task_tag,
              provider = excluded.provider,
              model = excluded.model,
              skills = excluded.skills,
              tags = excluded.tags,
              quality_score = excluded.quality_score,
              rating = excluded.rating,
              metadata_json = excluded.metadata_json
            """,
            (
                record.memory_id,
                record.session_id,
                record.turn_id,
                record.created_at.isoformat(),
                record.scope.value,
                record.kind,
                record.summary,
                record.content,
                record.task_tag.value if record.task_tag else None,
                record.provider_id,
                record.model_id,
                ",".join(record.skill_ids) if record.skill_ids else None,
                ",".join(record.tags) if record.tags else None,
                record.quality_score,
                record.rating,
                sqlite_helpers.json_dumps(record.metadata),
                record.metadata.get("source_event_id"),
            ),
        )


def _coerce_task_tag(value: TaskTag | None) -> TaskTag | None:
    if value is None:
        return None
    if isinstance(value, TaskTag):
        return value
    try:
        return TaskTag(value)
    except ValueError:
        return TaskTag.GENERAL


def _row_to_record(row: sqlite3.Row) -> MemoryRecord:
    from datetime import datetime

    task_tag = row["task_tag"]
    return MemoryRecord(
        memory_id=row["id"],
        scope=MemoryScope(row["scope"]),
        kind=row["kind"],
        summary=row["summary"],
        content=row["content"],
        tags=tuple(filter(None, (row["tags"] or "").split(","))),
        session_id=row["session_id"],
        turn_id=row["turn_id"],
        task_tag=TaskTag(task_tag) if task_tag else None,
        provider_id=row["provider"],
        model_id=row["model"],
        skill_ids=tuple(filter(None, (row["skills"] or "").split(","))),
        quality_score=float(row["quality_score"] or 0.0),
        rating=row["rating"],
        created_at=datetime.fromisoformat(row["created_at"]),
        metadata=sqlite_helpers.json_loads(row["metadata_json"]),
    )


def _format_optional(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):.3f}"
