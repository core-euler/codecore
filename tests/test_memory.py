from __future__ import annotations

import asyncio
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codecore.domain.enums import EventKind, MemoryScope, TaskTag
from codecore.domain.events import EventEnvelope
from codecore.domain.models import MemoryRecord
from codecore.infra import sqlite as sqlite_helpers
from codecore.memory.patterns import MemoryPatternMiner
from codecore.memory.rankings import HistoricalRanker
from codecore.memory.store import MemoryWritePolicy, SQLiteMemoryStore
from codecore.memory.summarizer import MemorySummarizer
from codecore.telemetry.tracker import TelemetryTracker


class MemoryRuntimeTest(unittest.TestCase):
    def test_write_policy_skips_trivial_general_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "registry.db"
            store = SQLiteMemoryStore(db_path)

            async def run() -> None:
                await store.publish(
                    EventEnvelope.create(
                        kind=EventKind.MODEL_INVOKED,
                        session_id="session-1",
                        turn_id="turn-1",
                        task_tag=TaskTag.GENERAL,
                        provider_id="mock",
                        model_id="mock-chat",
                        payload={"prompt": "hi", "response_text": "ok", "active_files": ()},
                    )
                )

            asyncio.run(run())
            self.assertEqual(store.stats()["count"], 0)
            store.close()

    def test_summarizer_extracts_highlights(self) -> None:
        summary = MemorySummarizer().summarize_turn(
            prompt="Review backend contract changes",
            response_text="1. Check handler boundary.\n2. Verify contract schema.\n3. Add regression test.",
            task_tag=TaskTag.REVIEW,
            skill_ids=("review", "backend"),
            active_files=("src/backend/api.py",),
        )
        self.assertIn("review:", summary.summary)
        self.assertGreaterEqual(len(summary.highlights), 2)
        self.assertIn("Check handler boundary", summary.content)

    def test_pattern_miner_groups_repeated_skill_patterns(self) -> None:
        now = datetime.now(timezone.utc)
        records = (
            MemoryRecord(
                memory_id="m1",
                scope=MemoryScope.OUTCOME,
                kind="turn.outcome",
                summary="review backend contracts",
                content="...",
                tags=("review", "backend"),
                task_tag=TaskTag.REVIEW,
                skill_ids=("review", "backend"),
                quality_score=0.9,
                rating=5,
                created_at=now,
                metadata={"file_names": ["contracts.py"]},
            ),
            MemoryRecord(
                memory_id="m2",
                scope=MemoryScope.OUTCOME,
                kind="turn.outcome",
                summary="review backend boundaries",
                content="...",
                tags=("review", "backend"),
                task_tag=TaskTag.REVIEW,
                skill_ids=("review", "backend"),
                quality_score=0.8,
                rating=4,
                created_at=now,
                metadata={"file_names": ["contracts.py"]},
            ),
        )
        patterns = MemoryPatternMiner().mine(records)
        labels = {pattern.label for pattern in patterns}
        self.assertIn("review, backend", labels)
        self.assertIn("contracts.py", labels)

    def test_ranker_recommends_best_model_for_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "registry.db"
            conn = sqlite_helpers.connect(db_path)
            conn.execute(
                "INSERT INTO sessions (id, started_at, task_tag, provider, model, skill) VALUES (?, ?, ?, ?, ?, ?)",
                ("s1", now_iso(), "review", "mistral", "codestral", "review"),
            )
            conn.execute(
                "INSERT INTO sessions (id, started_at, task_tag, provider, model, skill) VALUES (?, ?, ?, ?, ?, ?)",
                ("s2", now_iso(), "review", "deepseek", "ds-v3", "review"),
            )
            conn.execute(
                "INSERT INTO requests (id, session_id, turn_id, timestamp, model, model_alias, provider, task_tag, skills, input_tokens, output_tokens, latency_ms, cost_usd, rating) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("r1", "s1", "t1", now_iso(), "codestral-latest", "codestral", "mistral", "review", "review", 10, 20, 300, 0.2, 5),
            )
            conn.execute(
                "INSERT INTO requests (id, session_id, turn_id, timestamp, model, model_alias, provider, task_tag, skills, input_tokens, output_tokens, latency_ms, cost_usd, rating) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("r2", "s2", "t2", now_iso(), "deepseek-chat", "ds-v3", "deepseek", "review", "review", 10, 20, 600, 0.1, 3),
            )
            conn.commit()
            recommendation = HistoricalRanker().recommend_model(conn, task_tag=TaskTag.REVIEW)
            conn.close()
            self.assertEqual(recommendation.model, "codestral")
            self.assertEqual(recommendation.provider, "mistral")

    def test_store_promotes_feedback_into_higher_scope_memories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tracker = TelemetryTracker(temp_path / "registry.db", temp_path / "events")
            store = SQLiteMemoryStore(temp_path / "registry.db")

            async def run() -> None:
                started = EventEnvelope.create(
                    kind=EventKind.SESSION_STARTED,
                    session_id="session-42",
                    task_tag=TaskTag.REVIEW,
                )
                invoked = EventEnvelope.create(
                    kind=EventKind.MODEL_INVOKED,
                    session_id="session-42",
                    turn_id="turn-42",
                    task_tag=TaskTag.REVIEW,
                    provider_id="mistral",
                    model_id="codestral-latest",
                    skill_ids=("review",),
                    payload={
                        "model_alias": "codestral",
                        "prompt": "Need review findings for backend contract changes",
                        "response_text": "1. Check handler boundary. 2. Verify contract schema. 3. Add regression test.",
                        "active_files": ("src/backend/contracts.py",),
                    },
                )
                rated = EventEnvelope.create(
                    kind=EventKind.FEEDBACK_RECORDED,
                    session_id="session-42",
                    turn_id="turn-42",
                    task_tag=TaskTag.REVIEW,
                    payload={"rating": 5},
                )
                finished = EventEnvelope.create(
                    kind=EventKind.SESSION_FINISHED,
                    session_id="session-42",
                    task_tag=TaskTag.REVIEW,
                    provider_id="mistral",
                    model_id="codestral-latest",
                    skill_ids=("review",),
                )
                for event in (started, invoked, rated, finished):
                    await tracker.publish(event)
                    await store.publish(event)

            asyncio.run(run())
            scopes = {record.scope for record in store.list_recent(limit=20)}
            self.assertIn(MemoryScope.OUTCOME, scopes)
            self.assertIn(MemoryScope.PROJECT, scopes)
            self.assertIn(MemoryScope.GLOBAL, scopes)
            self.assertIn(MemoryScope.SESSION, scopes)
            store.close()

    def test_store_writes_governance_memory_on_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "registry.db"
            store = SQLiteMemoryStore(db_path)

            async def run() -> None:
                await store.publish(
                    EventEnvelope.create(
                        kind=EventKind.FALLBACK_TRIGGERED,
                        session_id="session-gov",
                        turn_id="turn-gov",
                        task_tag=TaskTag.CODE,
                        provider_id="deepseek",
                        model_id="deepseek-chat",
                        payload={
                            "failed_alias": "ds-v3",
                            "error": "timeout",
                            "next_provider_id": "mistral",
                            "next_model_id": "codestral-latest",
                            "next_alias": "codestral",
                        },
                    )
                )

            asyncio.run(run())
            scopes = {record.scope for record in store.list_recent(limit=10)}
            self.assertIn(MemoryScope.GOVERNANCE, scopes)
            store.close()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    unittest.main()
