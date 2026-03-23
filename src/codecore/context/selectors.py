"""Select file context snippets under a token budget."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..domain.enums import TaskTag
from .chunking import ContextChunk, FileChunker
from .manager import ContextManager, FileContextStats
from .token_budget import estimate_text_tokens

_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_\-]{2,}")


@dataclass(slots=True, frozen=True)
class FileSelection:
    path: str
    score: float
    source_tokens: int
    selected_tokens: int
    strategy: str
    line_count: int
    size_bytes: int


@dataclass(slots=True, frozen=True)
class ContextSelection:
    chunks: tuple[ContextChunk, ...]
    files: tuple[FileSelection, ...]
    total_tokens: int
    remaining_tokens: int


class ContextSelector:
    def __init__(self, context_manager: ContextManager) -> None:
        self._context_manager = context_manager

    def select(self, paths: list[str], budget_tokens: int, *, prompt: str = "", task_tag: TaskTag = TaskTag.GENERAL) -> ContextSelection:
        if budget_tokens <= 0 or not paths:
            return ContextSelection(chunks=(), files=(), total_tokens=0, remaining_tokens=max(0, budget_tokens))

        described = self._context_manager.describe_active_files(paths)
        if not described:
            return ContextSelection(chunks=(), files=(), total_tokens=0, remaining_tokens=max(0, budget_tokens))

        ranked = self._rank_files(described, prompt=prompt, task_tag=task_tag)
        per_chunk_budget = max(96, min(1200, budget_tokens // max(1, len(ranked))))
        chunker = FileChunker(max_tokens_per_chunk=per_chunk_budget)
        chunks: list[ContextChunk] = []
        file_reports: list[FileSelection] = []
        remaining = budget_tokens

        for score, stats in ranked:
            if remaining <= 0:
                break
            content = self._context_manager.read_text(stats.path, truncate=False)
            if content is None:
                continue

            selected_tokens = 0
            strategy = "excerpt"

            if stats.is_large:
                summary = self._context_manager.summarize_file(stats.path)
                if summary:
                    summary_tokens = estimate_text_tokens(summary)
                    if summary_tokens <= remaining:
                        chunks.append(
                            ContextChunk(
                                path=stats.path,
                                kind="summary",
                                start_line=1,
                                end_line=stats.line_count,
                                text=summary,
                                token_estimate=summary_tokens,
                                score=score,
                            )
                        )
                        remaining -= summary_tokens
                        selected_tokens += summary_tokens
                        strategy = "summary"
                if remaining >= max(192, per_chunk_budget // 2):
                    detail_chunks = chunker.chunk_text(stats.path, content, score=score)
                    if detail_chunks and detail_chunks[0].token_estimate <= remaining:
                        chunks.append(detail_chunks[0])
                        remaining -= detail_chunks[0].token_estimate
                        selected_tokens += detail_chunks[0].token_estimate
                        strategy = "summary+excerpt"
            else:
                detail_chunks = chunker.chunk_text(stats.path, content, score=score)
                for chunk in detail_chunks[:2]:
                    if chunk.token_estimate > remaining:
                        break
                    chunks.append(chunk)
                    remaining -= chunk.token_estimate
                    selected_tokens += chunk.token_estimate
                    if remaining <= 0:
                        break

            if selected_tokens > 0:
                file_reports.append(
                    FileSelection(
                        path=stats.path,
                        score=score,
                        source_tokens=stats.token_estimate,
                        selected_tokens=selected_tokens,
                        strategy=strategy,
                        line_count=stats.line_count,
                        size_bytes=stats.size_bytes,
                    )
                )

        total_tokens = sum(chunk.token_estimate for chunk in chunks)
        return ContextSelection(
            chunks=tuple(chunks),
            files=tuple(file_reports),
            total_tokens=total_tokens,
            remaining_tokens=remaining,
        )

    @staticmethod
    def render(chunks: tuple[ContextChunk, ...]) -> str:
        return "\n\n".join(chunk.render() for chunk in chunks)

    def _rank_files(self, files: tuple[FileContextStats, ...], *, prompt: str, task_tag: TaskTag) -> tuple[tuple[float, FileContextStats], ...]:
        prompt_keywords = {word.lower() for word in _WORD_RE.findall(prompt)}
        task_keyword = task_tag.value.lower()
        ranked: list[tuple[float, int, FileContextStats]] = []
        for index, stats in enumerate(files):
            path_lower = stats.path.lower()
            stem_lower = Path(stats.path).stem.lower()
            score = 0.0
            if task_keyword and task_keyword in path_lower:
                score += 3.0
            for keyword in prompt_keywords:
                if keyword in stem_lower:
                    score += 4.0
                elif keyword in path_lower:
                    score += 2.0
                if any(keyword in heading.lower() for heading in stats.headings):
                    score += 2.5
                if any(keyword in symbol.lower() for symbol in stats.symbols):
                    score += 2.0
            score += max(0.0, 1.5 - (stats.token_estimate / 4000))
            ranked.append((score, -index, stats))
        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return tuple((score, stats) for score, _, stats in ranked)
