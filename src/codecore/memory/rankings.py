"""Ranking and recommendation helpers over telemetry rows."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from ..domain.enums import TaskTag


@dataclass(slots=True, frozen=True)
class Recommendation:
    task_tag: str
    model: str | None
    provider: str | None
    score: float | None
    rationale: str


class HistoricalRanker:
    def model_rankings_by_task(self, conn: sqlite3.Connection) -> tuple[dict[str, float | int | None | str], ...]:
        rows = conn.execute(
            """
            SELECT COALESCE(task_tag, 'unknown') AS task_tag,
                   COALESCE(model_alias, model, 'unknown') AS model,
                   provider,
                   COUNT(*) AS requests,
                   AVG(rating) AS avg_rating,
                   AVG(latency_ms) AS avg_latency_ms,
                   SUM(cost_usd) AS total_cost_usd
            FROM requests
            GROUP BY COALESCE(task_tag, 'unknown'), COALESCE(model_alias, model, 'unknown'), provider
            """
        ).fetchall()
        ranked = []
        for row in rows:
            avg_rating = row["avg_rating"] or 0.0
            avg_latency = row["avg_latency_ms"] or 0.0
            total_cost = row["total_cost_usd"] or 0.0
            requests = row["requests"] or 0
            score = avg_rating * 2.4 + requests * 0.35 - avg_latency / 1200.0 - total_cost * 50.0
            ranked.append({**dict(row), "score": round(score, 3)})
        ranked.sort(key=lambda item: (item["score"], item["requests"]), reverse=True)
        return tuple(ranked)

    def route_rankings(self, conn: sqlite3.Connection, *, success_rating_threshold: int = 4) -> tuple[dict[str, float | int | None | str], ...]:
        rows = conn.execute(
            """
            SELECT provider,
                   COALESCE(model_alias, model, 'unknown') AS model,
                   COUNT(*) AS requests,
                   AVG(rating) AS avg_rating,
                   AVG(latency_ms) AS avg_latency_ms,
                   SUM(cost_usd) AS total_cost_usd,
                   SUM(CASE WHEN rating >= ? THEN 1 ELSE 0 END) AS successful_requests
            FROM requests
            GROUP BY provider, COALESCE(model_alias, model, 'unknown')
            """,
            (success_rating_threshold,),
        ).fetchall()
        ranked = []
        for row in rows:
            successful = row["successful_requests"] or 0
            total_cost = row["total_cost_usd"] or 0.0
            avg_rating = row["avg_rating"] or 0.0
            avg_latency = row["avg_latency_ms"] or 0.0
            cost_per_success = total_cost / successful if successful else None
            score = avg_rating * 2.6 + successful * 0.4 - avg_latency / 1200.0 - (cost_per_success or 0.0) * 25.0
            ranked.append({
                **dict(row),
                "cost_per_successful_task_usd": cost_per_success,
                "score": round(score, 3),
            })
        ranked.sort(key=lambda item: (item["score"], item["successful_requests"], item["requests"]), reverse=True)
        return tuple(ranked[:8])

    def skill_rankings_by_outcome(self, conn: sqlite3.Connection) -> tuple[dict[str, float | int | None | str], ...]:
        rows = conn.execute("SELECT skills, rating FROM requests WHERE skills IS NOT NULL AND skills != ''").fetchall()
        stats: dict[str, dict[str, float | int]] = {}
        for row in rows:
            rating = row["rating"]
            for skill in [item.strip() for item in str(row["skills"]).split(",") if item.strip()]:
                entry = stats.setdefault(skill, {"uses": 0, "rating_sum": 0.0, "rated": 0, "high_quality": 0})
                entry["uses"] += 1
                if rating is not None:
                    entry["rating_sum"] += float(rating)
                    entry["rated"] += 1
                    if rating >= 4:
                        entry["high_quality"] += 1
        ranked = []
        for skill, entry in stats.items():
            avg_rating = entry["rating_sum"] / entry["rated"] if entry["rated"] else None
            score = (avg_rating or 0.0) * 2.2 + entry["high_quality"] * 0.5 + entry["uses"] * 0.2
            ranked.append(
                {
                    "skill": skill,
                    "uses": entry["uses"],
                    "avg_rating": avg_rating,
                    "high_quality_uses": entry["high_quality"],
                    "score": round(score, 3),
                }
            )
        ranked.sort(key=lambda item: (item["score"], item["uses"]), reverse=True)
        return tuple(ranked[:8])

    def recommend_model(self, conn: sqlite3.Connection, *, task_tag: TaskTag | str | None) -> Recommendation:
        normalized_tag = self._normalize_task_tag(task_tag)
        rankings = self.model_rankings_by_task(conn)
        candidates = [row for row in rankings if row["task_tag"] == normalized_tag]
        if not candidates and normalized_tag != TaskTag.GENERAL.value:
            candidates = [row for row in rankings if row["task_tag"] == TaskTag.GENERAL.value]
        if not candidates:
            return Recommendation(
                task_tag=normalized_tag,
                model=None,
                provider=None,
                score=None,
                rationale="Insufficient history for recommendation.",
            )
        best = candidates[0]
        rationale = (
            f"Based on {best['requests']} requests with avg_rating={_fmt(best['avg_rating'])} "
            f"and avg_latency_ms={_fmt(best['avg_latency_ms'])}."
        )
        return Recommendation(
            task_tag=normalized_tag,
            model=str(best["model"]),
            provider=str(best["provider"] or "unknown"),
            score=float(best["score"]),
            rationale=rationale,
        )

    def _normalize_task_tag(self, task_tag: TaskTag | str | None) -> str:
        if task_tag is None:
            return TaskTag.GENERAL.value
        if isinstance(task_tag, TaskTag):
            return task_tag.value
        try:
            return TaskTag(task_tag).value
        except ValueError:
            return TaskTag.GENERAL.value


def _fmt(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):.3f}"
