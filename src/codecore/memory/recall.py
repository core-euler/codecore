"""Recall helpers for injecting memory into the prompt."""

from __future__ import annotations

from dataclasses import dataclass

from ..context.token_budget import estimate_text_tokens
from ..domain.enums import TaskTag
from ..domain.contracts import MemoryStore
from ..domain.models import MemoryRecord


@dataclass(slots=True, frozen=True)
class MemoryRecallPolicy:
    min_quality_score: float = 0.2

    def rank(
        self,
        records: tuple[MemoryRecord, ...],
        *,
        query: str,
        task_tag: TaskTag | None,
        active_skills: tuple[str, ...],
        active_files: tuple[str, ...],
    ) -> tuple[MemoryRecord, ...]:
        query_lower = query.lower()
        active_file_names = {item.rsplit("/", 1)[-1] for item in active_files}
        scored: list[tuple[float, MemoryRecord]] = []
        for record in records:
            if record.quality_score < self.min_quality_score and record.rating is None:
                continue
            score = record.quality_score * 4.0
            if record.task_tag == task_tag and task_tag is not None:
                score += 2.0
            skill_overlap = len(set(active_skills) & set(record.skill_ids))
            if skill_overlap:
                score += skill_overlap * 1.25
            file_overlap = len(active_file_names & set(record.metadata.get("file_names", ())))
            if file_overlap:
                score += file_overlap * 1.0
            if query_lower and query_lower in record.summary.lower():
                score += 1.5
            scored.append((score, record))
        scored.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
        return tuple(record for _, record in scored)


class MemoryRecallComposer:
    def __init__(self, memory_store: MemoryStore, *, policy: MemoryRecallPolicy | None = None) -> None:
        self._memory_store = memory_store
        self._policy = policy or MemoryRecallPolicy()

    async def compose(
        self,
        *,
        query: str,
        budget_tokens: int,
        limit: int = 3,
        task_tag: TaskTag | None = None,
        active_skills: tuple[str, ...] = (),
        active_files: tuple[str, ...] = (),
    ) -> tuple[str, tuple[MemoryRecord, ...]]:
        if budget_tokens <= 0:
            return "", ()
        memories = await self._memory_store.recall(query=query, limit=max(1, limit * 3))
        if not memories:
            return "", ()
        memories = self._policy.rank(
            memories,
            query=query,
            task_tag=task_tag,
            active_skills=active_skills,
            active_files=active_files,
        )
        selected: list[MemoryRecord] = []
        blocks: list[str] = []
        spent = 0
        for memory in memories:
            block = self._render(memory)
            tokens = estimate_text_tokens(block)
            if spent and spent + tokens > budget_tokens:
                continue
            if not spent and tokens > budget_tokens:
                continue
            selected.append(memory)
            blocks.append(block)
            spent += tokens
            if len(selected) >= limit:
                break
        if not blocks:
            return "", ()
        return "Relevant memory:\n" + "\n\n".join(blocks), tuple(selected)

    def _render(self, memory: MemoryRecord) -> str:
        tags = ", ".join(memory.tags[:6]) if memory.tags else "<none>"
        rating = str(memory.rating) if memory.rating is not None else "-"
        return (
            f"Memory [{memory.scope.value}/{memory.kind}]\n"
            f"summary: {memory.summary}\n"
            f"rating: {rating}\n"
            f"quality: {memory.quality_score:.2f}\n"
            f"tags: {tags}"
        )
