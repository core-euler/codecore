"""Status line rendering."""

from __future__ import annotations

from ..kernel.runtime_state import RuntimeState
from ..kernel.session import SessionRuntime


def _short_number(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}k"
    return str(value)


def _short_context_window(value: int | None) -> str:
    if value is None:
        return ""
    if value >= 1_000:
        return f" ({value / 1_000:.0f}K)"
    return f" ({value})"


def build_status_line(session: SessionRuntime, state: RuntimeState) -> str:
    model = state.active_model or state.manual_model_alias or "auto"
    model_text = f"{model}{_short_context_window(state.active_model_context_tokens)}"
    return (
        f"[codecore] model: {model_text}"
        f" * ctx: {session.last_context_file_count} files"
        f" * tok: {_short_number(session.last_context_token_count)}"
        f" * req: {session.request_count}"
        f" * cost: ${session.total_cost_usd:.4f}"
    )
