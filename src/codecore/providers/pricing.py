"""Request pricing helpers."""

from __future__ import annotations

from ..domain.models import ProviderRoute


def estimate_cost(route: ProviderRoute, input_tokens: int | None, output_tokens: int | None) -> float | None:
    if input_tokens is None or output_tokens is None:
        return None
    if route.cost_hint_in is None and route.cost_hint_out is None:
        return None
    total = 0.0
    if route.cost_hint_in is not None:
        total += (input_tokens / 1000.0) * route.cost_hint_in
    if route.cost_hint_out is not None:
        total += (output_tokens / 1000.0) * route.cost_hint_out
    return round(total, 8)
