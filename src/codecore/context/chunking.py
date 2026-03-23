"""Chunk prompt context into token-bounded snippets."""

from __future__ import annotations

from dataclasses import dataclass

from .token_budget import estimate_text_tokens


@dataclass(slots=True, frozen=True)
class ContextChunk:
    path: str
    kind: str
    start_line: int
    end_line: int
    text: str
    token_estimate: int
    score: float = 0.0

    def render(self) -> str:
        if self.kind == "summary":
            return f"FILE SUMMARY: {self.path}\n{self.text}"
        return f"FILE: {self.path} [lines {self.start_line}-{self.end_line}]\n```\n{self.text}\n```"


class FileChunker:
    def __init__(self, max_tokens_per_chunk: int = 900) -> None:
        self._max_tokens_per_chunk = max(64, max_tokens_per_chunk)

    def chunk_text(self, path: str, text: str, *, score: float = 0.0) -> tuple[ContextChunk, ...]:
        if not text:
            return ()

        lines = text.splitlines() or [text]
        chunks: list[ContextChunk] = []
        current_lines: list[str] = []
        start_line = 1

        for line_number, line in enumerate(lines, start=1):
            candidate_lines = current_lines + [line]
            candidate_text = "\n".join(candidate_lines)
            if current_lines and estimate_text_tokens(candidate_text) > self._max_tokens_per_chunk:
                text_block = "\n".join(current_lines)
                chunks.append(
                    ContextChunk(
                        path=path,
                        kind="excerpt",
                        start_line=start_line,
                        end_line=line_number - 1,
                        text=text_block,
                        token_estimate=estimate_text_tokens(text_block),
                        score=score,
                    )
                )
                current_lines = [line]
                start_line = line_number
                continue
            current_lines = candidate_lines

        if current_lines:
            text_block = "\n".join(current_lines)
            chunks.append(
                ContextChunk(
                    path=path,
                    kind="excerpt",
                    start_line=start_line,
                    end_line=len(lines),
                    text=text_block,
                    token_estimate=estimate_text_tokens(text_block),
                    score=score,
                )
            )
        return tuple(chunks)
