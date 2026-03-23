"""Helpers for classifying and summarizing runtime memories."""

from __future__ import annotations

import re
from uuid import uuid4

from ..domain.enums import MemoryScope, TaskTag
from ..domain.models import MemoryRecord
from .summarizer import MemorySummarizer, file_names

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_./-]+")


def normalize_terms(*parts: str) -> tuple[str, ...]:
    terms: list[str] = []
    seen: set[str] = set()
    for part in parts:
        for token in _TOKEN_RE.findall(part.lower()):
            if len(token) < 3:
                continue
            if token in seen:
                continue
            seen.add(token)
            terms.append(token)
    return tuple(terms)


def build_turn_memory(
    *,
    session_id: str,
    turn_id: str,
    prompt: str,
    response_text: str,
    task_tag: TaskTag | None,
    provider_id: str | None,
    model_id: str | None,
    skill_ids: tuple[str, ...] = (),
    active_files: tuple[str, ...] = (),
) -> MemoryRecord:
    turn_summary = MemorySummarizer().summarize_turn(
        prompt=prompt,
        response_text=response_text,
        task_tag=task_tag,
        skill_ids=skill_ids,
        active_files=active_files,
    )
    tag_terms = normalize_terms(prompt, response_text, " ".join(skill_ids), " ".join(active_files))
    return MemoryRecord(
        memory_id=str(uuid4()),
        scope=MemoryScope.OUTCOME,
        kind="turn.outcome",
        summary=turn_summary.summary,
        content=turn_summary.content,
        tags=tag_terms,
        session_id=session_id,
        turn_id=turn_id,
        task_tag=task_tag,
        provider_id=provider_id,
        model_id=model_id,
        skill_ids=skill_ids,
        quality_score=0.25,
        metadata={
            "active_files": list(active_files),
            "file_names": list(file_names(active_files)),
            "highlights": list(turn_summary.highlights),
        },
    )


def rating_to_quality(rating: int | None) -> float:
    if rating is None:
        return 0.25
    return max(0.0, min(1.0, rating / 5.0))
