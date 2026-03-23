"""Status line rendering."""

from __future__ import annotations

from ..kernel.runtime_state import RuntimeState
from ..kernel.session import SessionRuntime


def build_status_line(session: SessionRuntime, state: RuntimeState) -> str:
    provider = state.active_provider or "auto"
    model = state.active_model or state.manual_model_alias or "auto"
    return (
        f"[codecore] provider={provider}"
        f" | model={model}"
        f" | ctx={len(session.active_files)} files"
        f" | req={session.request_count}"
        f" | cost=${session.total_cost_usd:.4f}"
    )
