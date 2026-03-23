"""Append-only audit log for workspace file changes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(slots=True, frozen=True)
class FileChangeRecord:
    record_id: str
    session_id: str
    action: str
    timestamp: datetime
    path: str | None = None
    paths: tuple[str, ...] = ()
    diff: str | None = None
    backup_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class FileChangeAudit:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record_patch(
        self,
        *,
        session_id: str,
        path: str,
        diff: str,
        backup_path: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> FileChangeRecord:
        record = FileChangeRecord(
            record_id=str(uuid4()),
            session_id=session_id,
            action="patch_applied",
            timestamp=datetime.now(timezone.utc),
            path=path,
            diff=diff,
            backup_path=backup_path,
            metadata=dict(metadata or {}),
        )
        self._append(record)
        return record

    def record_restore(
        self,
        *,
        session_id: str,
        paths: tuple[str, ...],
        metadata: dict[str, Any] | None = None,
    ) -> FileChangeRecord:
        record = FileChangeRecord(
            record_id=str(uuid4()),
            session_id=session_id,
            action="restore",
            timestamp=datetime.now(timezone.utc),
            paths=paths,
            metadata=dict(metadata or {}),
        )
        self._append(record)
        return record

    def _append(self, record: FileChangeRecord) -> None:
        payload = {
            "record_id": record.record_id,
            "session_id": record.session_id,
            "action": record.action,
            "timestamp": record.timestamp.isoformat(),
            "path": record.path,
            "paths": list(record.paths),
            "diff": record.diff,
            "backup_path": record.backup_path,
            "metadata": record.metadata,
        }
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
