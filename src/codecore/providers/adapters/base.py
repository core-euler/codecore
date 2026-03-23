"""Adapter factory for provider routes."""

from __future__ import annotations

from .mock_adapter import MockModelAdapter
from ...domain.contracts import ModelGateway
from ...domain.models import ProviderRoute


class AdapterFactory:
    def create(self, route: ProviderRoute) -> ModelGateway:
        if route.provider_id == "mock":
            return MockModelAdapter(route)
        from ..litellm_adapter import LiteLLMAdapter

        return LiteLLMAdapter(route)
