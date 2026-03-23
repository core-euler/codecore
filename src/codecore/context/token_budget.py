"""Token budget helpers for prompt composition."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil


_DEF_RESERVE_OUTPUT_TOKENS = 4096
_DEF_SAFETY_MARGIN_TOKENS = 1024


def estimate_text_tokens(text: str) -> int:
    """Rough token estimate that is cheap enough for every prompt build."""
    if not text:
        return 0
    return max(1, ceil(len(text) / 4))


@dataclass(slots=True, frozen=True)
class PromptBudgetSnapshot:
    max_prompt_tokens: int
    soft_limit_tokens: int
    reserved_output_tokens: int
    safety_margin_tokens: int
    base_tokens: int
    available_context_tokens: int
    compact_required: bool


class TokenBudgetPlanner:
    def __init__(
        self,
        *,
        max_prompt_tokens: int,
        auto_compact_threshold_pct: int,
        default_reserved_output_tokens: int = _DEF_RESERVE_OUTPUT_TOKENS,
        safety_margin_tokens: int = _DEF_SAFETY_MARGIN_TOKENS,
    ) -> None:
        self._max_prompt_tokens = max_prompt_tokens
        self._auto_compact_threshold_pct = auto_compact_threshold_pct
        self._default_reserved_output_tokens = default_reserved_output_tokens
        self._safety_margin_tokens = safety_margin_tokens

    def plan(self, *segments: str, reserved_output_tokens: int | None = None) -> PromptBudgetSnapshot:
        reserve = (
            reserved_output_tokens
            if reserved_output_tokens is not None
            else min(self._default_reserved_output_tokens, max(256, self._max_prompt_tokens // 4))
        )
        base_tokens = sum(estimate_text_tokens(segment) for segment in segments if segment)
        soft_limit_tokens = max(0, (self._max_prompt_tokens * self._auto_compact_threshold_pct) // 100)
        available_context_tokens = max(0, soft_limit_tokens - reserve - self._safety_margin_tokens - base_tokens)
        compact_required = base_tokens >= max(0, soft_limit_tokens - reserve)
        return PromptBudgetSnapshot(
            max_prompt_tokens=self._max_prompt_tokens,
            soft_limit_tokens=soft_limit_tokens,
            reserved_output_tokens=reserve,
            safety_margin_tokens=self._safety_margin_tokens,
            base_tokens=base_tokens,
            available_context_tokens=available_context_tokens,
            compact_required=compact_required,
        )
