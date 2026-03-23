"""SQLite helpers for telemetry projections."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  task_tag TEXT,
  provider TEXT,
  model TEXT,
  skill TEXT
);

CREATE TABLE IF NOT EXISTS requests (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  turn_id TEXT,
  timestamp TEXT NOT NULL,
  model TEXT,
  model_alias TEXT,
  provider TEXT,
  task_tag TEXT,
  skills TEXT,
  input_tokens INTEGER,
  output_tokens INTEGER,
  latency_ms INTEGER,
  cost_usd REAL,
  rating INTEGER,
  FOREIGN KEY(session_id) REFERENCES sessions(id)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    _ensure_request_column(conn, "turn_id", "TEXT")
    _ensure_request_column(conn, "model_alias", "TEXT")
    _ensure_request_column(conn, "task_tag", "TEXT")
    _ensure_request_column(conn, "skills", "TEXT")
    conn.commit()
    return conn


def _ensure_request_column(conn: sqlite3.Connection, column_name: str, column_type: str) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(requests)").fetchall()}
    if column_name not in columns:
        conn.execute(f"ALTER TABLE requests ADD COLUMN {column_name} {column_type}")


def json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def json_loads(value: str | None) -> dict:
    if not value:
        return {}
    loaded = json.loads(value)
    return loaded if isinstance(loaded, dict) else {}
