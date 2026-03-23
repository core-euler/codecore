"""Helpers for mapping provider manifests to capability metadata."""

from __future__ import annotations

from ..domain.models import ModelCapabilities, ProviderRoute


def route_capabilities(route: ProviderRoute) -> ModelCapabilities:
    return ModelCapabilities(
        supports_streaming=True,
        supports_tools=route.supports_tools,
        supports_json=route.supports_json,
        supports_vision=route.supports_vision,
        max_context_tokens=route.max_context_tokens,
    )
