"""Provider health refresh and caching."""

from __future__ import annotations

import asyncio
import os
import time

from ..domain.enums import HealthState
from ..domain.models import HealthStatus, ProviderRoute
from .adapters.base import AdapterFactory
from .registry import ProviderRegistry


class ProviderHealthService:
    def __init__(self, registry: ProviderRegistry, adapter_factory: AdapterFactory, ttl_seconds: int = 300) -> None:
        self._registry = registry
        self._adapter_factory = adapter_factory
        self._ttl_seconds = ttl_seconds
        self._snapshot: dict[str, HealthStatus] = {}
        self._last_refresh = 0.0

    @staticmethod
    def route_key(route: ProviderRoute) -> str:
        return f"{route.provider_id}:{route.alias or route.model_id}"

    async def refresh(self, *, force: bool = False) -> dict[str, HealthStatus]:
        now = time.monotonic()
        if not force and self._snapshot and (now - self._last_refresh) < self._ttl_seconds:
            return self._snapshot

        routes = self._registry.ordered_routes()
        statuses = await asyncio.gather(*(self._check_route(route) for route in routes))
        snapshot = {self.route_key(route): status for route, status in zip(routes, statuses, strict=True)}
        self._snapshot = snapshot
        self._last_refresh = now
        return snapshot

    async def status_for(self, route: ProviderRoute) -> HealthStatus:
        snapshot = await self.refresh()
        return snapshot[self.route_key(route)]

    def last_snapshot(self) -> dict[str, HealthStatus]:
        return dict(self._snapshot)

    async def _check_route(self, route: ProviderRoute) -> HealthStatus:
        if route.auth_strategy and route.auth_strategy.startswith("env:"):
            env_name = route.auth_strategy.removeprefix("env:")
            if not os.getenv(env_name):
                return HealthStatus(
                    state=HealthState.UNAVAILABLE,
                    checked_at=HealthStatus.unknown().checked_at,
                    detail="missing API key",
                )
        adapter = self._adapter_factory.create(route)
        return await adapter.health()
