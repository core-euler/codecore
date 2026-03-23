"""Read-only analytics over the telemetry SQLite database and event logs."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ..domain.enums import EventKind, TaskTag
from ..memory.patterns import MemoryPatternMiner
from ..memory.rankings import HistoricalRanker, Recommendation
from ..memory.store import SQLiteMemoryStore


@dataclass(slots=True, frozen=True)
class AnalyticsReport:
    overview: dict[str, float | int | None]
    task_breakdown: tuple[dict[str, float | int | None], ...]
    model_rankings: tuple[dict[str, float | int | None | str], ...]
    skill_rankings: tuple[dict[str, float | int | None | str], ...]
    task_model_rankings: tuple[dict[str, float | int | None | str], ...]
    route_rankings: tuple[dict[str, float | int | None | str], ...]
    provider_reliability: tuple[dict[str, float | int | None | str], ...]
    memory_overview: dict[str, float | int | None]
    memory_patterns: tuple[dict[str, float | int | None | str], ...]
    recommendation: Recommendation

    def render_text(self) -> str:
        lines = [
            "overview:",
            f"  sessions={self.overview['sessions']}",
            f"  requests={self.overview['requests']}",
            f"  total_cost_usd={_format_float(self.overview['total_cost_usd'])}",
            f"  cost_per_successful_task_usd={_format_float(self.overview['cost_per_successful_task_usd'])}",
            f"  avg_latency_ms={_format_float(self.overview['avg_latency_ms'])}",
            f"  avg_rating={_format_float(self.overview['avg_rating'])}",
            "memory:",
            f"  count={self.memory_overview['count']}",
            f"  avg_rating={_format_float(self.memory_overview['avg_rating'])}",
            f"  avg_quality_score={_format_float(self.memory_overview['avg_quality_score'])}",
            "recommendation:",
            f"  task_tag={self.recommendation.task_tag}",
            f"  model={self.recommendation.model or '<none>'}",
            f"  provider={self.recommendation.provider or '<none>'}",
            f"  score={_format_float(self.recommendation.score)}",
            f"  rationale={self.recommendation.rationale}",
        ]
        lines.append("task_breakdown:")
        lines.extend(_render_rows(self.task_breakdown, ("task_tag", "requests", "avg_rating", "avg_latency_ms")))
        lines.append("model_rankings:")
        lines.extend(_render_rows(self.model_rankings, ("model", "requests", "avg_rating", "score", "total_cost_usd")))
        lines.append("skill_rankings:")
        lines.extend(_render_rows(self.skill_rankings, ("skill", "uses", "avg_rating", "high_quality_uses", "score")))
        lines.append("task_model_rankings:")
        lines.extend(_render_rows(self.task_model_rankings, ("task_tag", "model", "provider", "requests", "avg_rating", "score")))
        lines.append("route_rankings:")
        lines.extend(
            _render_rows(
                self.route_rankings,
                ("provider", "model", "successful_requests", "avg_rating", "cost_per_successful_task_usd", "score"),
            )
        )
        lines.append("provider_reliability:")
        lines.extend(_render_rows(self.provider_reliability, ("provider", "attempts", "successes", "fallbacks", "reliability")))
        lines.append("memory_patterns:")
        lines.extend(_render_rows(self.memory_patterns, ("kind", "label", "count", "avg_rating", "avg_quality_score")))
        return "\n".join(lines)


class TelemetryAnalytics:
    def __init__(self, db_path: Path, event_dir: Path) -> None:
        self._db_path = db_path
        self._event_dir = event_dir
        self._ranker = HistoricalRanker()
        self._pattern_miner = MemoryPatternMiner()

    def build_report(self, *, task_tag: TaskTag | str | None = None) -> AnalyticsReport:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            overview = self._overview(conn)
            task_breakdown = self._task_breakdown(conn)
            model_rankings = self._model_rankings(conn)
            skill_rankings = self._ranker.skill_rankings_by_outcome(conn)
            task_model_rankings = self._ranker.model_rankings_by_task(conn)[:8]
            route_rankings = self._ranker.route_rankings(conn)
            memory_overview = self._memory_overview(conn)
            recommendation = self._ranker.recommend_model(conn, task_tag=task_tag)
        finally:
            conn.close()
        memory_patterns = self._memory_patterns()
        provider_reliability = self._provider_reliability()
        return AnalyticsReport(
            overview=overview,
            task_breakdown=task_breakdown,
            model_rankings=model_rankings,
            skill_rankings=skill_rankings,
            task_model_rankings=task_model_rankings,
            route_rankings=route_rankings,
            provider_reliability=provider_reliability,
            memory_overview=memory_overview,
            memory_patterns=memory_patterns,
            recommendation=recommendation,
        )

    def _overview(self, conn: sqlite3.Connection) -> dict[str, float | int | None]:
        sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        row = conn.execute(
            "SELECT COUNT(*), SUM(cost_usd), AVG(latency_ms), AVG(rating), SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) FROM requests"
        ).fetchone()
        total_cost = row[1]
        successful = row[4] or 0
        return {
            "sessions": sessions,
            "requests": row[0] or 0,
            "total_cost_usd": total_cost,
            "cost_per_successful_task_usd": (total_cost / successful) if total_cost is not None and successful else None,
            "avg_latency_ms": row[2],
            "avg_rating": row[3],
        }

    def _task_breakdown(self, conn: sqlite3.Connection) -> tuple[dict[str, float | int | None], ...]:
        rows = conn.execute(
            """
            SELECT COALESCE(task_tag, 'unknown') AS task_tag,
                   COUNT(*) AS requests,
                   AVG(rating) AS avg_rating,
                   AVG(latency_ms) AS avg_latency_ms
            FROM requests
            GROUP BY COALESCE(task_tag, 'unknown')
            ORDER BY requests DESC, task_tag ASC
            """
        ).fetchall()
        return tuple(dict(row) for row in rows)

    def _model_rankings(self, conn: sqlite3.Connection) -> tuple[dict[str, float | int | None | str], ...]:
        rows = conn.execute(
            """
            SELECT COALESCE(model_alias, model, 'unknown') AS model,
                   COUNT(*) AS requests,
                   AVG(rating) AS avg_rating,
                   AVG(latency_ms) AS avg_latency_ms,
                   SUM(cost_usd) AS total_cost_usd
            FROM requests
            GROUP BY COALESCE(model_alias, model, 'unknown')
            ORDER BY requests DESC, model ASC
            """
        ).fetchall()
        ranked = []
        for row in rows:
            avg_rating = row["avg_rating"] or 0.0
            avg_latency = row["avg_latency_ms"] or 0.0
            total_cost = row["total_cost_usd"] or 0.0
            score = avg_rating * 2.0 + row["requests"] * 0.3 - avg_latency / 1000.0 - total_cost * 50.0
            ranked.append({**dict(row), "score": round(score, 3)})
        ranked.sort(key=lambda item: (item["score"], item["requests"]), reverse=True)
        return tuple(ranked[:5])

    def _memory_overview(self, conn: sqlite3.Connection) -> dict[str, float | int | None]:
        try:
            row = conn.execute("SELECT COUNT(*), AVG(rating), AVG(quality_score) FROM memories").fetchone()
        except sqlite3.OperationalError:
            return {"count": 0, "avg_rating": None, "avg_quality_score": None}
        return {
            "count": row[0] or 0,
            "avg_rating": row[1],
            "avg_quality_score": row[2],
        }

    def _memory_patterns(self) -> tuple[dict[str, float | int | None | str], ...]:
        store = SQLiteMemoryStore(self._db_path)
        try:
            records = store.list_recent(limit=120)
        finally:
            store.close()
        patterns = self._pattern_miner.mine(records, limit=6)
        return tuple(
            {
                "kind": pattern.kind,
                "label": pattern.label,
                "count": pattern.count,
                "avg_rating": pattern.avg_rating,
                "avg_quality_score": pattern.avg_quality_score,
            }
            for pattern in patterns
        )

    def _provider_reliability(self) -> tuple[dict[str, float | int | None | str], ...]:
        stats: dict[str, dict[str, int]] = {}
        if not self._event_dir.exists():
            return ()
        for path in sorted(self._event_dir.glob("*.jsonl")):
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    record = json.loads(line)
                    provider = record.get("provider_id") or record.get("payload", {}).get("next_provider_id")
                    if not provider:
                        continue
                    entry = stats.setdefault(provider, {"attempts": 0, "successes": 0, "fallbacks": 0})
                    kind = record.get("kind")
                    if kind == EventKind.PROVIDER_SELECTED.value:
                        entry["attempts"] += 1
                    elif kind == EventKind.MODEL_INVOKED.value:
                        entry["successes"] += 1
                    elif kind == EventKind.FALLBACK_TRIGGERED.value:
                        entry["fallbacks"] += 1
        ranked = []
        for provider, entry in stats.items():
            attempts = max(entry["attempts"], entry["successes"] + entry["fallbacks"])
            reliability = entry["successes"] / attempts if attempts else None
            ranked.append(
                {
                    "provider": provider,
                    "attempts": attempts,
                    "successes": entry["successes"],
                    "fallbacks": entry["fallbacks"],
                    "reliability": reliability,
                }
            )
        ranked.sort(key=lambda item: ((item["reliability"] or 0.0), item["attempts"]), reverse=True)
        return tuple(ranked[:8])


def _render_rows(rows: tuple[dict[str, float | int | None | str], ...], columns: tuple[str, ...]) -> list[str]:
    if not rows:
        return ["  <none>"]
    rendered: list[str] = []
    for row in rows:
        parts = []
        for column in columns:
            value = row.get(column)
            if isinstance(value, float):
                value = _format_float(value)
            parts.append(f"{column}={value}")
        rendered.append("  " + " | ".join(parts))
    return rendered


def _format_float(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):.3f}"
