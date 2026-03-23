"""Provider registry and route lookup."""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.models import ProviderRoute
from .manifests import ProviderManifest, ProviderModelManifest, ProviderRegistryManifest


@dataclass(slots=True, frozen=True)
class RegisteredProviderRoute:
    provider: ProviderManifest
    model: ProviderModelManifest

    def to_route(self) -> ProviderRoute:
        return ProviderRoute(
            provider_id=self.provider.provider_id,
            model_id=self.model.id,
            alias=self.model.alias,
            priority=self.provider.priority,
            vpn_required=self.provider.vpn_required,
            cost_hint_in=self.model.cost_per_1k_in,
            cost_hint_out=self.model.cost_per_1k_out,
            transport=self.provider.transport,
            base_url=self.provider.base_url,
            auth_strategy=self.provider.auth_strategy,
            supports_tools=self.model.supports_tools,
            supports_json=self.model.supports_json,
            supports_vision=self.model.supports_vision,
            max_context_tokens=self.model.max_context,
        )

    @property
    def route_key(self) -> str:
        alias = self.model.alias or self.model.id
        return f"{self.provider.provider_id}:{alias}"


class ProviderRegistry:
    def __init__(self, manifest: ProviderRegistryManifest) -> None:
        self._routes = tuple(
            RegisteredProviderRoute(provider=provider, model=model)
            for provider in manifest.providers
            for model in provider.models
        )

    def list_registered(self) -> tuple[RegisteredProviderRoute, ...]:
        return self._routes

    def list_routes(self) -> tuple[ProviderRoute, ...]:
        return tuple(route.to_route() for route in self._routes)

    def by_alias(self, alias: str) -> ProviderRoute | None:
        for route in self._routes:
            if route.model.alias == alias:
                return route.to_route()
        return None

    def by_model_id(self, model_id: str) -> ProviderRoute | None:
        for route in self._routes:
            if route.model.id == model_id:
                return route.to_route()
        return None

    def ordered_routes(self) -> tuple[ProviderRoute, ...]:
        return tuple(sorted(self.list_routes(), key=lambda route: (route.priority, route.provider_id, route.model_id)))
