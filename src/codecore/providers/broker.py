"""Policy-driven provider selection."""

from __future__ import annotations

from ..domain.contracts import ProviderBroker
from ..domain.enums import HealthState
from ..domain.models import ChatRequest, ProviderRoute
from .health import ProviderHealthService
from .registry import ProviderRegistry


class BrokerError(RuntimeError):
    """Raised when no route can satisfy the request."""


class PolicyDrivenBroker(ProviderBroker):
    def __init__(
        self,
        registry: ProviderRegistry,
        health_service: ProviderHealthService,
        *,
        preferred_aliases: tuple[str, ...] = (),
        allow_vpn_routes: bool = True,
    ) -> None:
        self._registry = registry
        self._health_service = health_service
        self._preferred_aliases = preferred_aliases
        self._allow_vpn_routes = allow_vpn_routes
        self._preference_index = {alias: index for index, alias in enumerate(preferred_aliases)}

    async def select_route(self, request: ChatRequest) -> ProviderRoute:
        return (await self.candidate_routes(request))[0]

    async def candidate_routes(self, request: ChatRequest) -> tuple[ProviderRoute, ...]:
        snapshot = await self._health_service.refresh()

        if request.model_hint:
            explicit = self._registry.by_alias(request.model_hint) or self._registry.by_model_id(request.model_hint)
            if explicit is None:
                raise BrokerError(f"Unknown model alias: {request.model_hint}")
            status = snapshot[self._health_service.route_key(explicit)]
            if status.state in {HealthState.HEALTHY, HealthState.DEGRADED}:
                return (explicit,)
            raise BrokerError(f"Requested model is unavailable: {request.model_hint}")

        candidates: list[ProviderRoute] = []
        for route in self._registry.ordered_routes():
            if route.vpn_required and not self._allow_vpn_routes:
                continue
            status = snapshot[self._health_service.route_key(route)]
            if status.state in {HealthState.HEALTHY, HealthState.DEGRADED}:
                candidates.append(route)

        if candidates:
            return tuple(sorted(candidates, key=self._route_rank))

        raise BrokerError("No healthy provider routes available")

    def _route_rank(self, route: ProviderRoute) -> tuple[int, int, str, str]:
        alias = route.alias or route.model_id
        preference_rank = self._preference_index.get(alias, len(self._preferred_aliases))
        return (preference_rank, route.priority, route.provider_id, route.model_id)
