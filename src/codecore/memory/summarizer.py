"""Compact summarization helpers for memory records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..domain.enums import TaskTag

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass(slots=True, frozen=True)
class TurnSummary:
    summary: str
    content: str
    highlights: tuple[str, ...]


class MemorySummarizer:
    def summarize_turn(
        self,
        *,
        prompt: str,
        response_text: str,
        task_tag: TaskTag | None,
        skill_ids: tuple[str, ...] = (),
        active_files: tuple[str, ...] = (),
    ) -> TurnSummary:
        prompt_line = self._compact_line(prompt, limit=160)
        response_line = self._compact_line(response_text, limit=220)
        highlights = self._highlights(response_text)
        summary = f"{task_tag.value if task_tag else 'general'}: {prompt_line} -> {response_line}"
        sections = [
            f"task_tag: {task_tag.value if task_tag else 'general'}",
            f"skills: {', '.join(skill_ids) if skill_ids else '<none>'}",
            f"active_files: {', '.join(active_files) if active_files else '<none>'}",
            f"prompt: {prompt.strip()}",
            f"response_summary: {response_line}",
        ]
        if highlights:
            sections.append("highlights:")
            sections.extend(f"- {item}" for item in highlights)
        return TurnSummary(summary=summary, content="\n".join(sections), highlights=highlights)

    def summarize_record(self, content: str, *, limit: int = 180) -> str:
        return self._compact_line(content, limit=limit)

    def _highlights(self, response_text: str) -> tuple[str, ...]:
        lines = [line.strip(" -*\t") for line in response_text.splitlines() if line.strip()]
        extracted: list[str] = []
        for line in lines:
            if line.startswith(("1.", "2.", "3.", "4.", "5.")) or len(extracted) < 2:
                compact = self._compact_line(line, limit=120)
                if compact and compact not in extracted:
                    extracted.append(compact)
            if len(extracted) >= 4:
                break
        if extracted:
            return tuple(extracted)
        sentences = [self._compact_line(sentence, limit=120) for sentence in _SENTENCE_SPLIT_RE.split(response_text) if sentence.strip()]
        return tuple(item for item in sentences[:3] if item)

    def _compact_line(self, text: str, *, limit: int) -> str:
        compact = " ".join(text.strip().split())
        if len(compact) <= limit:
            return compact
        return compact[: max(0, limit - 3)].rstrip() + "..."


def file_names(paths: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(Path(path).name for path in paths)
