"""Mining repeated development patterns from stored memories."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from ..domain.models import MemoryRecord


@dataclass(slots=True, frozen=True)
class MemoryPattern:
    kind: str
    label: str
    count: int
    avg_rating: float | None
    avg_quality_score: float
    examples: tuple[str, ...] = ()


class MemoryPatternMiner:
    def mine(self, records: tuple[MemoryRecord, ...], *, limit: int = 8) -> tuple[MemoryPattern, ...]:
        patterns: list[MemoryPattern] = []
        patterns.extend(self._top_skill_patterns(records, limit=limit // 2 or 1))
        patterns.extend(self._top_tag_patterns(records, limit=limit // 2 or 1))
        patterns.extend(self._top_file_patterns(records, limit=limit // 2 or 1))
        patterns.sort(key=lambda item: (item.avg_quality_score, item.count), reverse=True)
        return tuple(patterns[:limit])

    def _top_skill_patterns(self, records: tuple[MemoryRecord, ...], *, limit: int) -> tuple[MemoryPattern, ...]:
        buckets: dict[str, list[MemoryRecord]] = defaultdict(list)
        for record in records:
            if record.skill_ids:
                label = ", ".join(record.skill_ids)
                buckets[label].append(record)
        return self._to_patterns("skills", buckets, limit=limit)

    def _top_tag_patterns(self, records: tuple[MemoryRecord, ...], *, limit: int) -> tuple[MemoryPattern, ...]:
        counts = Counter(tag for record in records for tag in record.tags[:8])
        buckets: dict[str, list[MemoryRecord]] = defaultdict(list)
        for record in records:
            for tag in record.tags[:8]:
                if counts[tag] > 1:
                    buckets[tag].append(record)
        return self._to_patterns("tags", buckets, limit=limit)

    def _top_file_patterns(self, records: tuple[MemoryRecord, ...], *, limit: int) -> tuple[MemoryPattern, ...]:
        buckets: dict[str, list[MemoryRecord]] = defaultdict(list)
        for record in records:
            for file_name in record.metadata.get("file_names", [])[:4]:
                buckets[file_name].append(record)
        return self._to_patterns("files", buckets, limit=limit)

    def _to_patterns(self, kind: str, buckets: dict[str, list[MemoryRecord]], *, limit: int) -> tuple[MemoryPattern, ...]:
        patterns: list[MemoryPattern] = []
        for label, records in buckets.items():
            if len(records) < 2:
                continue
            ratings = [record.rating for record in records if record.rating is not None]
            avg_rating = sum(ratings) / len(ratings) if ratings else None
            avg_quality = sum(record.quality_score for record in records) / len(records)
            examples = tuple(record.summary for record in records[:2])
            patterns.append(
                MemoryPattern(
                    kind=kind,
                    label=label,
                    count=len(records),
                    avg_rating=avg_rating,
                    avg_quality_score=avg_quality,
                    examples=examples,
                )
            )
        patterns.sort(key=lambda item: (item.avg_quality_score, item.count), reverse=True)
        return tuple(patterns[:limit])
